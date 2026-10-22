"""LLM 앞에서 질문을 규칙으로 분류하는 정책 게이트와 거절 문구 상수.

거절 문구는 여기 상수만 쓰고, 인-아웃 세트의 expected_traits 에도 같은 문자열을 쓴다.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

REFUSAL_CROSS_TENANT = "다른 회사(테넌트)의 데이터는 조회할 수 없습니다."
REFUSAL_WRITE = "이 Agent는 읽기 전용이라 데이터를 수정·삭제·추가할 수 없습니다."
REFUSAL_SECRET = "시스템 내부 정보나 비밀 값은 제공할 수 없습니다."
REFUSAL_OUT_OF_SCOPE = (
    "지원하지 않는 질문입니다. 다음과 같은 질문을 할 수 있습니다.\n"
    "- 비용 집계: '이번 달 팀별 비용 알려줘', '고객지원팀 서비스별 9월 비용은?'\n"
    "- 전월 대비 변화: '지난달 대비 왜 늘었어?', '줄어든 서비스 알려줘'\n"
    "- 모델 교체 what-if: 'claude-sonnet을 claude-haiku로 바꾸면 얼마나 줄어?'"
)

REFUSALS = {
    "cross_tenant": REFUSAL_CROSS_TENANT,
    "write": REFUSAL_WRITE,
    "secret": REFUSAL_SECRET,
    "out_of_scope": REFUSAL_OUT_OF_SCOPE,
}

SECRET_PATTERN = re.compile(
    r"시스템\s*프롬프트|system\s*prompt|비밀\s*키|비밀\s*값|secret|api\s*키|api\s*key|환경\s*변수|"
    r"jwt|토큰\s*값|접속\s*토큰|인증\s*토큰|access\s*token|이전\s*지시|지시(를|는)?\s*무시|ignore\s+(all\s+)?previous",
    re.IGNORECASE,
)
WRITE_PATTERN = re.compile(
    r"삭제|지워|수정해|추가해|입력해|바꿔\s*줘|변경해|업데이트|덮어써|delete|update|insert|drop\s+table",
    re.IGNORECASE,
)
OTHER_COMPANY_PATTERN = re.compile(r"다른\s*회사|타사|타\s*회사|다른\s*테넌트")
FORECAST_PATTERN = re.compile(r"예측|전망|다음\s*달|내년|향후")
COST_PATTERN = re.compile(
    r"비용|금액|얼마|증가|감소|늘었|늘어|줄었|줄어|팀|서비스|기능|모델|미귀속|요금|cost", re.IGNORECASE
)


@dataclass(frozen=True)
class PolicyDecision:
    """정책 판정 결과. cls 가 'allowed' 가 아니면 refusal 문구를 그대로 답한다."""

    cls: str
    refusal: str | None = None


def tenant_names() -> dict:
    """tenant_id → 회사 이름."""
    rows = json.loads((DATA / "tenants.json").read_text(encoding="utf-8"))
    return {r["tenant_id"]: r["name"] for r in rows}


def classify(question: str, tenant_id: str) -> PolicyDecision:
    """질문을 secret → write → cross_tenant → out_of_scope → allowed 순서로 판정한다."""
    q = question.strip()
    if SECRET_PATTERN.search(q):
        return PolicyDecision("secret", REFUSAL_SECRET)
    if WRITE_PATTERN.search(q):
        return PolicyDecision("write", REFUSAL_WRITE)
    others = [name for tid, name in tenant_names().items() if tid != tenant_id]
    if OTHER_COMPANY_PATTERN.search(q) or any(name.lower() in q.lower() for name in others):
        return PolicyDecision("cross_tenant", REFUSAL_CROSS_TENANT)
    if FORECAST_PATTERN.search(q) or not COST_PATTERN.search(q):
        return PolicyDecision("out_of_scope", REFUSAL_OUT_OF_SCOPE)
    return PolicyDecision("allowed")
