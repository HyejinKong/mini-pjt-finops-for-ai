"""POST /query API. 신원은 서명된 더미 JWT 로만 받는다.

실행: uvicorn src.api:app --reload
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src import agent

load_dotenv()

DATA = Path(__file__).resolve().parent.parent / "data"
ALGORITHM = "HS256"


@dataclass(frozen=True)
class Principal:
    """검증된 요청자. tenant_id 는 users.json 에서 정한다."""

    user_id: str
    tenant_id: str


class QueryRequest(BaseModel):
    """요청 본문. question 하나만 받는다."""

    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1000)


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


def issue_dummy_token(user_id: str) -> str:
    """테스트와 채점용 더미 JWT 를 발급한다. 회사 정보는 서버가 users.json 에서 정한다."""
    if user_id not in users():
        raise ValueError(f"알 수 없는 사용자: {user_id}")
    return jwt.encode({"sub": user_id}, jwt_secret(), algorithm=ALGORITHM)


def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    """Authorization: Bearer 토큰을 검증해 Principal 을 만든다. 실패하면 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")
    try:
        claims = jwt.decode(authorization.removeprefix("Bearer "), jwt_secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    user = users().get(claims.get("sub"))
    if user is None:
        raise HTTPException(status_code=401, detail="알 수 없는 사용자입니다.")
    return Principal(user_id=user["user_id"], tenant_id=user["tenant_id"])


app = FastAPI(title="FinOps for AI Agent")


@app.post("/query")
def query(body: QueryRequest, principal: Principal = Depends(get_principal)) -> dict:
    """질문을 받아 answer, contexts, trace 를 돌려준다."""
    return agent.answer(body.question, principal.tenant_id)
