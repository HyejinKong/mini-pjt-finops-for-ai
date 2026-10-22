"""채점 스크립트의 숫자 근거 규칙이 LLM 이 직접 계산한 숫자를 잡는지 검사한다."""

import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evaluation"))

from run_eval import check_grounded
from src.tools import TenantRepo, build_tools


def model_breakdown():
    """판다소프트 9월 모델별 집계 결과."""
    tools = {t.name: t for t in build_tools(TenantRepo("panda-soft"))}
    return tools["get_cost_breakdown"].invoke({"group_by": ["model"], "month": "2026-09"})


def contexts_of(out):
    """도구 결과 하나를 contexts 형식으로 감싼다."""
    return [{"tool": "get_cost_breakdown", "content": json.dumps(out, ensure_ascii=False)}]


def money(m):
    """도구 금액을 답변 표기 '$X (약 N원)' 로 쓴다."""
    return f"${float(m['usd']):,.2f} (약 {m['krw']:,}원)"


def test_grounded_answer_passes():
    out = model_breakdown()
    answer = (f"{out['rows'][0]['model']} {money(out['rows'][0])}, 미귀속 {money(out['unattributed'])}, "
              f"전체 합계 {money(out['total'])}, 미귀속 제외 {money(out['tagged_total'])}")
    assert check_grounded(answer, contexts_of(out)) == []


def test_invented_total_is_caught():
    # 4-3 첫 bedrock 실행의 q03 처럼, 미귀속이 포함된 total 에 미귀속을 또 더한 합계를 지어낸다
    out = model_breakdown()
    invented_usd = Decimal(out["total"]["usd"]) + Decimal(out["unattributed"]["usd"])
    invented = {"usd": str(invented_usd), "krw": int(invented_usd * 1400)}
    answer = f"**소계** {money(out['total'])}\n**전체 합계: {money(invented)}**"
    assert check_grounded(answer, contexts_of(out)) == [f"{invented_usd:,.2f}", f"{invented['krw']:,}"]


def test_invented_share_is_caught():
    out = model_breakdown()
    answer = f"{out['rows'][0]['model']} 가 전체의 약 97% 입니다. ${out['rows'][0]['usd']}"
    assert check_grounded(answer, contexts_of(out)) == ["97"]


def test_sign_is_ignored():
    contexts = [{"content": json.dumps({"delta_usd": "-5.06", "delta_krw": -7084, "pct_or_new": "-13.9"})}]
    assert check_grounded("감소액 $5.06 (약 -7,084원), -13.9%", contexts) == []
