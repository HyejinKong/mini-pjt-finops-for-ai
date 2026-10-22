"""GET /dashboard/data 의 토큰 검증, 테넌트 격리, 숫자가 도구 결과 그대로인지 검사한다. LLM 은 쓰지 않는다."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import agent, api
from src.tools import TenantRepo, build_dashboard_tools, build_tools

EXP = json.loads((Path(__file__).resolve().parent.parent / "evaluation" / "expected_values.json").read_text(encoding="utf-8"))
HBE_TOKEN = "test-static-token-honeybee"
PDS_TOKEN = "test-static-token-panda"


@pytest.fixture
def client(monkeypatch):
    """기본 모드(회사별 고정 토큰). 대시보드는 LLM 을 부르면 안 된다."""
    monkeypatch.setenv("AUTH_MODE", "static")
    monkeypatch.setenv("TENANT_TOKEN_HONEYBEE_ELECTRONICS", HBE_TOKEN)
    monkeypatch.setenv("TENANT_TOKEN_PANDA_SOFT", PDS_TOKEN)
    monkeypatch.setattr(agent, "run_agent", lambda *a: pytest.fail("대시보드 데이터는 LLM 을 부르면 안 된다"))
    return TestClient(api.app)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def amounts_in(value):
    """값 안에 나오는 0 이 아닌 USD 금액(소수 둘째 자리 문자열) 전체."""
    found = set()

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str) and "." in v and len(v.split(".")[1]) == 2:
            try:
                if Decimal(v) != 0:
                    found.add(str(abs(Decimal(v))))
            except ArithmeticError:
                pass

    walk(value)
    return found


def amounts(tenant):
    """정답값(일별 포함)에 나오는 금액 전체."""
    return amounts_in(EXP[tenant])


def dashboard_only_amounts(tenant, month):
    """정답값에 없는 대시보드 전용 금액(일별, 8월 대 7월 전월 대비)을 그 회사 도구로 직접 계산한다."""
    repo = TenantRepo(tenant)
    tools = {t.name: t for t in build_tools(repo) + build_dashboard_tools(repo)}
    outputs = [tools["get_daily_trend"].invoke({"month": month})] + [
        tools["get_mom_change"].invoke({"dimension": [d], "direction": direction,
                                        "this_month": month, "last_month": api.previous_month(month)})
        for d in ("team", "service", "model") for direction in ("increase", "decrease")
    ]
    return amounts_in(outputs)


@pytest.mark.parametrize("headers", [{}, bearer("wrong-token"), bearer(""), {"Authorization": HBE_TOKEN}])
def test_bad_token_401(client, headers):
    assert client.get("/dashboard/data", headers=headers).status_code == 401


@pytest.mark.parametrize("token,own,other,other_name", [
    (HBE_TOKEN, "honeybee-electronics", "panda-soft", "판다소프트"),
    (PDS_TOKEN, "panda-soft", "honeybee-electronics", "꿀벌전자"),
])
@pytest.mark.parametrize("month", ["2026-09", "2026-08"])
def test_no_other_tenant_data(client, token, own, other, other_name, month):
    r = client.get("/dashboard/data", params={"month": month}, headers=bearer(token))
    assert r.status_code == 200
    text = json.dumps(r.json(), ensure_ascii=False)
    # 대시보드 전용 금액은 우연히 다른 회사 금액과 같을 수 있어(TASKS 7-2 결정) 다른 회사에만 있는 금액으로 검사한다
    other_only = amounts(other) - amounts(own) - dashboard_only_amounts(own, month)
    assert not any(f'"{a}"' in text for a in other_only)
    assert other_name not in text and other not in text


def test_numbers_are_tool_outputs(client):
    body = client.get("/dashboard/data", headers=bearer(PDS_TOKEN)).json()
    repo = TenantRepo("panda-soft")
    tools = {t.name: t for t in build_tools(repo) + build_dashboard_tools(repo)}
    periods = {"this_month": "2026-09", "last_month": "2026-08"}
    for d in ("team", "service", "model"):
        assert body["breakdown"][d] == tools["get_cost_breakdown"].invoke({"group_by": [d]})
        for direction in ("increase", "decrease"):
            assert body["mom"][direction][d] == tools["get_mom_change"].invoke({"dimension": [d], "direction": direction, **periods})
    assert body["cross"] == tools["get_cost_breakdown"].invoke({"group_by": ["team", "model"]})
    assert body["daily"] == tools["get_daily_trend"].invoke({"month": "2026-09"})


@pytest.mark.parametrize("tenant,token", [("honeybee-electronics", HBE_TOKEN), ("panda-soft", PDS_TOKEN)])
def test_kpi_matches_expected(client, tenant, token):
    kpi = client.get("/dashboard/data", headers=bearer(token)).json()["kpi"]
    by_month = EXP[tenant]["by_month"]
    assert (kpi["month"], kpi["previous_month"]) == ("2026-09", "2026-08")
    assert (kpi["total"]["this_usd"], kpi["total"]["last_usd"]) == (by_month["2026-09"]["total"], by_month["2026-08"]["total"])
    assert kpi["unattributed"]["usd"] == by_month["2026-09"]["unattributed"]
    assert "share_pct" in kpi["unattributed"]


def test_august_compares_with_july(client):
    body = client.get("/dashboard/data", params={"month": "2026-08"}, headers=bearer(HBE_TOKEN)).json()
    assert body["kpi"]["previous_month"] == "2026-07"
    assert body["kpi"]["total"]["this_usd"] == EXP["honeybee-electronics"]["by_month"]["2026-08"]["total"]
    assert body["mom"]["increase"]["team"]["last_month"] == "2026-07"


def test_scope_applies_to_mom_only(client):
    body = client.get("/dashboard/data", params={"scope_team": "고객지원팀"}, headers=bearer(HBE_TOKEN)).json()
    assert set(body["mom"]["increase"]) == {"service", "model"}
    assert all(m["scope"]["team"] == "고객지원팀" and "unattributed" not in m for m in body["mom"]["increase"].values())
    assert body["breakdown"]["team"]["scope"] == {"team": None, "service": None}
    assert body["kpi"]["total"]["this_usd"] == EXP["honeybee-electronics"]["by_month"]["2026-09"]["total"]


def test_empty_scope_means_whole_tenant(client):
    body = client.get("/dashboard/data", params={"scope_team": "", "scope_service": ""}, headers=bearer(HBE_TOKEN)).json()
    assert set(body["mom"]["increase"]) == {"team", "service", "model"}


@pytest.mark.parametrize("params", [{"month": "2026-07"}, {"month": "2025-13"}, {"scope_team": "물류팀"}, {"scope_service": "없는서비스"}])
def test_unknown_month_or_scope_400(client, params):
    r = client.get("/dashboard/data", params=params, headers=bearer(HBE_TOKEN))
    assert r.status_code == 400
    assert "rows" not in r.text
