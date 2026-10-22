"""POST /query API 와 대시보드 데이터(GET /dashboard/data). 회사는 Authorization 헤더의 토큰으로만 정한다.

AUTH_MODE=static(기본): .env 의 회사별 고정 토큰과 비교한다.
AUTH_MODE=jwt(선택): 서명된 더미 JWT 를 검증하고 sub 로 회사를 찾는다. exp 가 없거나 지나면 거절한다.

실행: uvicorn src.api:app --reload  (브라우저 시연 화면: http://127.0.0.1:8000/ 대시보드 + 질문 패널, 화면 코드는 src/ui.py)
시연용 JWT 발급: python -m src.api issue hbe-lead-01
"""

import argparse
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src import agent, ui
from src.tools import TenantRepo, build_dashboard_tools, build_tools, load_settings

load_dotenv()

DATA = Path(__file__).resolve().parent.parent / "data"
ALGORITHM = "HS256"
AUTH_MODES = ("static", "jwt")
TOKEN_TTL = timedelta(hours=1)
DASHBOARD_DIMENSIONS = ("team", "service", "model")


@dataclass(frozen=True)
class Principal:
    """검증된 요청자. 회사 안에서는 모든 역할이 같은 데이터를 보므로 tenant_id 만 둔다."""

    tenant_id: str


class QueryRequest(BaseModel):
    """요청 본문. question 하나만 받는다."""

    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1000)


def auth_mode() -> str:
    """AUTH_MODE 를 환경변수에서 읽는다. 없으면 static."""
    mode = os.getenv("AUTH_MODE", "static")
    if mode not in AUTH_MODES:
        raise RuntimeError(f"AUTH_MODE 는 {AUTH_MODES} 중 하나여야 합니다: {mode}")
    return mode


def tenant_ids() -> list[str]:
    """등록된 회사 tenant_id 목록."""
    rows = json.loads((DATA / "tenants.json").read_text(encoding="utf-8"))
    return [r["tenant_id"] for r in rows]


def token_env_name(tenant_id: str) -> str:
    """회사 고정 토큰을 담는 환경변수 이름. 예: panda-soft → TENANT_TOKEN_PANDA_SOFT."""
    return "TENANT_TOKEN_" + tenant_id.upper().replace("-", "_")


def resolve_static(token: str) -> str | None:
    """회사별 고정 토큰과 비교해 tenant_id 를 돌려준다. 값이 비어 있는 회사는 인증하지 않는다."""
    for tenant_id in tenant_ids():
        expected = os.getenv(token_env_name(tenant_id), "")
        if expected and hmac.compare_digest(token.encode(), expected.encode()):
            return tenant_id
    return None


def jwt_secret() -> str:
    """JWT 서명 비밀키를 환경변수에서 읽는다."""
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET 이 .env 에 없습니다.")
    return secret


def users() -> dict:
    """user_id → 사용자 정보."""
    rows = json.loads((DATA / "users.json").read_text(encoding="utf-8"))
    return {u["user_id"]: u for u in rows}


def issue_dummy_token(user_id: str, ttl: timedelta = TOKEN_TTL) -> str:
    """테스트·채점·시연용 더미 JWT 를 발급한다. ttl 뒤에 만료된다. 회사 정보는 서버가 users.json 에서 정한다."""
    if user_id not in users():
        raise ValueError(f"알 수 없는 사용자: {user_id}")
    exp = datetime.now(timezone.utc) + ttl
    return jwt.encode({"sub": user_id, "exp": exp}, jwt_secret(), algorithm=ALGORITHM)


def resolve_jwt(token: str) -> str | None:
    """서명된 더미 JWT 를 검증하고 sub 사용자의 tenant_id 를 돌려준다. exp·sub 가 없거나 만료되면 None."""
    try:
        claims = jwt.decode(token, jwt_secret(), algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None
    user = users().get(claims.get("sub"))
    return user["tenant_id"] if user else None


def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    """Authorization: Bearer 토큰을 AUTH_MODE 방식으로 검증해 Principal 을 만든다. 실패하면 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")
    resolve = resolve_jwt if auth_mode() == "jwt" else resolve_static
    tenant_id = resolve(authorization.removeprefix("Bearer "))
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    return Principal(tenant_id=tenant_id)


app = FastAPI(title="FinOps for AI Agent")
app.include_router(ui.router)


@app.post("/query")
def query(body: QueryRequest, principal: Principal = Depends(get_principal)) -> dict:
    """질문을 받아 answer, contexts, trace 를 돌려준다."""
    return agent.answer(body.question, principal.tenant_id)


def previous_month(month: str) -> str:
    """'YYYY-MM' 의 전달을 돌려준다."""
    year, mon = map(int, month.split("-"))
    return f"{year - 1}-12" if mon == 1 else f"{year}-{mon - 1:02d}"


def checked(result: dict) -> dict:
    """도구가 오류(모르는 팀·서비스·달)를 돌려주면 400 으로 바꾼다."""
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/dashboard/data")
def dashboard_data(
    month: str = "2026-09",
    scope_team: str | None = None,
    scope_service: str | None = None,
    principal: Principal = Depends(get_principal),
) -> dict:
    """대시보드 패널 숫자를 LLM 없이 도구를 직접 불러 돌려준다. 회사는 토큰으로만 정한다.
    month 는 이번 달·지난달 중 하나이고 그 전달과 비교한다. 범위(scope_team, scope_service)는 전월 대비 패널에만 쓴다."""
    settings = load_settings()
    if month not in (settings["this_month"], settings["last_month"]):
        raise HTTPException(status_code=400, detail=f"month 는 {settings['this_month']} 또는 {settings['last_month']} 입니다.")
    scope = {"team": scope_team or None, "service": scope_service or None}
    last = previous_month(month)
    repo = TenantRepo(principal.tenant_id)
    tools = {t.name: t for t in build_tools(repo) + build_dashboard_tools(repo)}
    breakdown, mom_change = tools["get_cost_breakdown"], tools["get_mom_change"]
    periods = {"this_month": month, "last_month": last}
    by_dimension = {d: checked(breakdown.invoke({"group_by": [d], "month": month})) for d in DASHBOARD_DIMENSIONS}
    overall = checked(mom_change.invoke({"dimension": ["team"], **periods}))
    mom = {
        direction: {
            d: checked(mom_change.invoke({"dimension": [d], "direction": direction, **periods, **scope}))
            for d in DASHBOARD_DIMENSIONS if scope.get(d) is None
        }
        for direction in ("increase", "decrease")
    }
    tenant = next(t for t in json.loads((DATA / "tenants.json").read_text(encoding="utf-8"))
                  if t["tenant_id"] == principal.tenant_id)
    return {
        "tenant": {"tenant_id": tenant["tenant_id"], "name": tenant["name"]},
        "kpi": {"month": month, "previous_month": last, "total": overall["total"],
                "unattributed": by_dimension["team"]["unattributed"]},
        "breakdown": by_dimension,
        "cross": checked(breakdown.invoke({"group_by": ["team", "model"], "month": month})),
        "mom": mom,
        "daily": checked(tools["get_daily_trend"].invoke({"month": month})),
    }


def main() -> None:
    """시연용 명령. issue <user_id> 로 JWT 선택 모드에서 쓸 토큰을 출력한다."""
    parser = argparse.ArgumentParser(description="FinOps Agent API 도우미 명령")
    sub = parser.add_subparsers(dest="command", required=True)
    issue = sub.add_parser("issue", help="user_id 로 더미 JWT 발급(AUTH_MODE=jwt 에서 사용)")
    issue.add_argument("user_id")
    args = parser.parse_args()
    if args.command == "issue":
        print(issue_dummy_token(args.user_id))


if __name__ == "__main__":
    main()
