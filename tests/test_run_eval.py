"""채점 스크립트의 숫자 근거 규칙이 LLM 이 직접 계산한 숫자를 잡는지 검사한다."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evaluation"))

from run_eval import check_grounded
from src.tools import TenantRepo, build_tools


def model_breakdown_contexts():
    """q03(판다소프트 9월 모델별)과 같은 도구 결과 contexts."""
    tools = {t.name: t for t in build_tools(TenantRepo("panda-soft"))}
    out = tools["get_cost_breakdown"].invoke({"group_by": "model", "month": "2026-09"})
    return [{"tool": "get_cost_breakdown", "content": json.dumps(out, ensure_ascii=False)}]


def test_grounded_answer_passes():
    answer = ("claude-haiku $308.05 (약 431,270원), 미귀속 $116.81 (약 163,534원), "
              "전체 합계 $791.43 (약 1,108,002원), 미귀속 제외 $674.62 (약 944,468원)")
    assert check_grounded(answer, model_breakdown_contexts()) == []


def test_invented_total_is_caught():
    # 4-3 첫 bedrock 실행의 q03: 미귀속이 포함된 total 에 미귀속을 또 더했다
    answer = "**소계** $791.43 (약 1,108,002원)\n**전체 합계: $908.24 (약 1,271,536원)**"
    assert check_grounded(answer, model_breakdown_contexts()) == ["908.24", "1,271,536"]


def test_invented_share_is_caught():
    answer = "claude-haiku 가 전체의 약 39% 입니다. $308.05"
    assert check_grounded(answer, model_breakdown_contexts()) == ["39"]


def test_sign_is_ignored():
    contexts = [{"content": json.dumps({"delta_usd": "-5.06", "delta_krw": -7084, "pct_or_new": "-13.9"})}]
    assert check_grounded("감소액 $5.06 (약 -7,084원), -13.9%", contexts) == []
