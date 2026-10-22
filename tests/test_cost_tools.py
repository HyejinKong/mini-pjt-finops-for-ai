"""1일차 도구 결과가 생성기가 독립적으로 계산한 정답값과 정확히 일치하는지 검사한다."""

import inspect
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from src.tools import TenantRepo, build_dashboard_tools, build_tools

ROOT = Path(__file__).resolve().parent.parent
EXP = json.loads((ROOT / "evaluation" / "expected_values.json").read_text(encoding="utf-8"))
TENANTS = list(EXP)


def tools_for(tenant):
    """도구 이름 → 도구."""
    return {t.name: t for t in build_tools(TenantRepo(tenant))}


@pytest.mark.parametrize("tenant", TENANTS)
@pytest.mark.parametrize("month", ["2026-09", "2026-08"])
@pytest.mark.parametrize("group_by,key", [("team", "team"), ("service", "service"), ("feature", "feature"), ("model", "model_id")])
def test_breakdown_matches_expected(tenant, month, group_by, key):
    out = tools_for(tenant)["get_cost_breakdown"].invoke({"group_by": [group_by], "month": month})
    exp = EXP[tenant]["by_month"][month]
    assert {r[group_by]: r["usd"] for r in out["rows"]} == exp[key]
    assert out["unattributed"]["usd"] == exp["unattributed"]
    assert out["total"]["usd"] == exp["total"]


@pytest.mark.parametrize("tenant", TENANTS)
def test_drilldown_by_team(tenant):
    tool = tools_for(tenant)["get_cost_breakdown"]
    for team, services in EXP[tenant]["drilldown_service_by_team"].items():
        out = tool.invoke({"group_by": ["service"], "team": team})
        assert {r["service"]: r["usd"] for r in out["rows"]} == services
        assert "unattributed" not in out


@pytest.mark.parametrize("tenant", TENANTS)
@pytest.mark.parametrize("direction", ["increase", "decrease"])
@pytest.mark.parametrize("dimension,key", [("team", "team"), ("service", "service"), ("model", "model_id")])
def test_mom_matches_expected(tenant, direction, dimension, key):
    out = tools_for(tenant)["get_mom_change"].invoke({"dimension": [dimension], "direction": direction})
    got = [{"key": i[dimension], **{k: i[k] for k in ("this_usd", "last_usd", "delta_usd", "pct_or_new")}} for i in out["items"]]
    assert got == EXP[tenant][f"mom_{direction}"][key]
    assert out["unattributed"]["key"] == "미귀속"


def test_krw_uses_fixed_rate():
    out = tools_for("panda-soft")["get_cost_breakdown"].invoke({"group_by": ["team"]})
    for r in out["rows"]:
        assert r["krw"] == round(float(r["usd"]) * 1400)


@pytest.mark.parametrize("direction", ["increase", "decrease"])
def test_mom_krw_matches_usd(direction):
    out = tools_for("honeybee-electronics")["get_mom_change"].invoke({"dimension": ["service"], "direction": direction})
    for i in out["items"] + [out["unattributed"]]:
        for p in ("this", "last", "delta"):
            assert i[f"{p}_krw"] == round(float(i[f"{p}_usd"]) * 1400)


def test_total_includes_unattributed_once():
    out = tools_for("panda-soft")["get_cost_breakdown"].invoke({"group_by": ["model"]})
    cents = lambda m: round(float(m["usd"]) * 100)
    assert cents(out["tagged_total"]) == sum(cents(r) for r in out["rows"])
    assert abs(cents(out["total"]) - cents(out["tagged_total"]) - cents(out["unattributed"])) <= 1


def test_unknown_team_returns_error_not_amounts():
    out = tools_for("honeybee-electronics")["get_cost_breakdown"].invoke({"group_by": ["service"], "team": "물류팀"})
    assert "error" in out and "rows" not in out


COLUMN = {"team": "team", "service": "service", "feature": "feature", "model": "model_id"}
MOM_FIELDS = ("this_usd", "last_usd", "delta_usd", "pct_or_new")


def mom_items(out, dims):
    """get_mom_change 항목을 정답값(생성기) 형식으로 바꾼다."""
    return [{**{COLUMN[d]: i[d] for d in dims}, **{k: i[k] for k in MOM_FIELDS}} for i in out["items"]]


@pytest.mark.parametrize("tenant", TENANTS)
@pytest.mark.parametrize("direction", ["increase", "decrease"])
@pytest.mark.parametrize("a,b", [("team", "service"), ("team", "model"), ("service", "model")])
def test_mom_two_dimensions_match_expected(tenant, direction, a, b):
    out = tools_for(tenant)["get_mom_change"].invoke({"dimension": [a, b], "direction": direction})
    assert mom_items(out, (a, b)) == EXP[tenant]["multi"]["mom_cross"][direction][f"{COLUMN[a]},{COLUMN[b]}"]
    assert out["unattributed"]["key"] == "미귀속"


@pytest.mark.parametrize("tenant", TENANTS)
@pytest.mark.parametrize("direction", ["increase", "decrease"])
@pytest.mark.parametrize("dim", ["service", "model"])
def test_mom_scoped_to_team_matches_expected(tenant, direction, dim):
    tool = tools_for(tenant)["get_mom_change"]
    for scope, exp in EXP[tenant]["multi"]["mom_scoped"][direction].items():
        out = tool.invoke({"dimension": [dim], "direction": direction, "team": scope.removeprefix("team=")})
        assert mom_items(out, (dim,)) == exp[COLUMN[dim]]
        assert "unattributed" not in out


def test_mom_rejects_unknown_team_and_bad_dimension():
    tool = tools_for("honeybee-electronics")["get_mom_change"]
    assert "error" in tool.invoke({"dimension": ["model"], "team": "물류팀"})
    assert "error" in tool.invoke({"dimension": ["team", "team"]})
PAIRS = [("team", "service"), ("team", "feature"), ("team", "model"), ("service", "feature"), ("service", "model"),
         ("feature", "model")]


@pytest.mark.parametrize("tenant", TENANTS)
@pytest.mark.parametrize("month", ["2026-09", "2026-08"])
@pytest.mark.parametrize("a,b", PAIRS)
def test_cross_table_matches_expected(tenant, month, a, b):
    out = tools_for(tenant)["get_cost_breakdown"].invoke({"group_by": [a, b], "month": month})
    exp = EXP[tenant]["multi"]["cross"][month][f"{COLUMN[a]},{COLUMN[b]}"]
    assert {(r[a], r[b]): r["usd"] for r in out["rows"]} == {(c[COLUMN[a]], c[COLUMN[b]]): c["usd"] for c in exp}
    by_month = EXP[tenant]["by_month"][month]
    for d in (a, b):
        assert {s[d]: s["usd"] for s in out["subtotals"][d]} == by_month[COLUMN[d]]
    assert out["total"]["usd"] == by_month["total"] and out["tagged_total"]["usd"] == by_month["tagged"]


@pytest.mark.parametrize("tenant", TENANTS)
@pytest.mark.parametrize("group_by", [["model"], ["team", "model"]])
def test_unattributed_split_by_model_only(tenant, group_by):
    out = tools_for(tenant)["get_cost_breakdown"].invoke({"group_by": group_by})
    exp = EXP[tenant]["multi"]["unattributed_by_model"]["2026-09"]
    assert {m["model"]: m["usd"] for m in out["unattributed"]["by_model"]} == exp
    assert out["unattributed"]["usd"] == EXP[tenant]["by_month"]["2026-09"]["unattributed"]
    assert "by_model" not in tools_for(tenant)["get_cost_breakdown"].invoke({"group_by": ["team"]})["unattributed"]


@pytest.mark.parametrize("group_by", [[], ["team", "team"], ["team", "service", "model"]])
def test_group_by_must_be_one_or_two_distinct(group_by):
    out = tools_for("panda-soft")["get_cost_breakdown"].invoke({"group_by": group_by})
    assert "error" in out and "rows" not in out


@pytest.mark.parametrize("tenant", TENANTS)
def test_whatif_matches_expected(tenant):
    tool = tools_for(tenant)["simulate_model_swap"]
    for w in EXP[tenant]["whatif"]:
        out = tool.invoke({"from_model": w["x"], "to_model": w["y"]})
        assert (out["input_tokens"], out["output_tokens"]) == (w["input_tokens"], w["output_tokens"])
        assert (out["before"]["usd"], out["after"]["usd"]) == (w["before_usd"], w["after_usd"])
        assert out["change"]["kind"] == w["kind"]
        assert out["change"]["usd"] == w["saving_usd"].lstrip("-")
        assert out["assumption"] == "토큰 수 동일 가정, 품질 차이 미반영"


def test_whatif_before_equals_actual_cost():
    tools = tools_for("honeybee-electronics")
    actual = tools["get_cost_breakdown"].invoke({"group_by": ["model"], "team": "고객지원팀"})
    for row in actual["rows"]:
        to_model = "claude-haiku" if row["model"] == "nova-lite" else "nova-lite"
        out = tools["simulate_model_swap"].invoke({"from_model": row["model"], "to_model": to_model, "team": "고객지원팀"})
        assert out["before"]["usd"] == row["usd"]


def test_whatif_edge_cases():
    tool = tools_for("honeybee-electronics")["simulate_model_swap"]
    unknown = tool.invoke({"from_model": "gpt-4", "to_model": "claude-haiku"})
    assert "error" in unknown and unknown["models"] == ["claude-haiku", "claude-sonnet", "nova-lite", "nova-pro"]
    assert tool.invoke({"from_model": "claude-haiku", "to_model": "claude-haiku"})["kind"] == "no_change"
    no_usage = tool.invoke({"from_model": "nova-pro", "to_model": "nova-lite", "month": "2026-08"})
    assert no_usage["kind"] == "no_usage" and "nova-pro" not in no_usage["models_in_scope"]
    assert "error" in tool.invoke({"from_model": "claude-sonnet", "to_model": "claude-haiku", "team": "물류팀"})


def test_tools_take_no_tenant_argument():
    repo = TenantRepo("honeybee-electronics")
    for t in build_tools(repo) + build_dashboard_tools(repo):
        params = set(t.args) | set(inspect.signature(t.func).parameters)
        assert not any("tenant" in p for p in params), t.name


def test_tool_output_has_no_other_tenant_data():
    pds_amounts = set(EXP["panda-soft"]["by_month"]["2026-09"]["team"].values()) | {EXP["panda-soft"]["by_month"]["2026-09"]["total"]}
    tools = tools_for("honeybee-electronics")
    outputs = [
        tools["get_cost_breakdown"].invoke({"group_by": g})
        for g in (["team"], ["service"], ["feature"], ["model"], ["team", "model"])
    ] + [tools["get_mom_change"].invoke({"dimension": d}) for d in (["team"], ["service"], ["model"], ["team", "model"])]
    text = json.dumps(outputs, ensure_ascii=False)
    assert "판다소프트" not in text
    assert not any(f'"{a}"' in text for a in pds_amounts)


def test_unknown_tenant_rejected():
    for bad in ("../panda-soft", "../usage/panda-soft", "acme"):
        with pytest.raises(ValueError):
            TenantRepo(bad)


# ---------- 대시보드 KPI 필드와 일별 추이 (묶음 7) ----------

def pct1(part, whole):
    """정답 금액 문자열 두 개로 비율(%)을 소수 한 자리로 계산한다."""
    return str((Decimal(part) * 100 / Decimal(whole)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


@pytest.mark.parametrize("tenant", TENANTS)
@pytest.mark.parametrize("month", ["2026-09", "2026-08"])
def test_unattributed_share_pct(tenant, month):
    out = tools_for(tenant)["get_cost_breakdown"].invoke({"group_by": ["team"], "month": month})
    exp = EXP[tenant]["by_month"][month]
    assert out["unattributed"]["share_pct"] == pct1(exp["unattributed"], exp["total"])
    assert "unattributed" not in tools_for(tenant)["get_cost_breakdown"].invoke({"group_by": ["service"], "team": "고객지원팀"})


@pytest.mark.parametrize("tenant", TENANTS)
def test_mom_total_line(tenant):
    out = tools_for(tenant)["get_mom_change"].invoke({"dimension": ["team"]})
    this, last = EXP[tenant]["by_month"]["2026-09"]["total"], EXP[tenant]["by_month"]["2026-08"]["total"]
    t = out["total"]
    assert (t["this_usd"], t["last_usd"]) == (this, last)
    assert abs(Decimal(t["delta_usd"]) - (Decimal(this) - Decimal(last))) <= Decimal("0.01")
    # 도구는 반올림 전 금액으로 계산하므로, 반올림된 정답으로 다시 계산한 값과 0.1%p 까지 다를 수 있다
    assert abs(Decimal(t["pct_or_new"]) - Decimal(pct1(t["delta_usd"], last))) <= Decimal("0.1")
    for p in ("this", "last", "delta"):
        assert t[f"{p}_krw"] == round(float(t[f"{p}_usd"]) * 1400)


def test_mom_total_line_in_scope_excludes_unattributed():
    out = tools_for("panda-soft")["get_mom_change"].invoke({"dimension": ["service"], "team": "고객지원팀"})
    services_this = EXP["panda-soft"]["drilldown_service_by_team"]["고객지원팀"]
    assert abs(Decimal(out["total"]["this_usd"]) - sum(Decimal(v) for v in services_this.values())) <= Decimal("0.01")
    assert "unattributed" not in out


@pytest.mark.parametrize("tenant", TENANTS)
@pytest.mark.parametrize("month", ["2026-09", "2026-08"])
def test_daily_trend_matches_expected(tenant, month):
    out = build_dashboard_tools(TenantRepo(tenant))[0].invoke({"month": month})
    exp = EXP[tenant]["daily"][month]
    assert {d["date"]: d["usd"] for d in out["days"]} == exp["total"]
    assert {d["date"]: d["unattributed_usd"] for d in out["days"]} == exp["unattributed"]
    assert out["total"]["usd"] == EXP[tenant]["by_month"][month]["total"]
    assert all(d["krw"] == round(float(d["usd"]) * 1400) for d in out["days"])


def test_daily_trend_is_not_an_agent_tool():
    repo = TenantRepo("honeybee-electronics")
    assert "get_daily_trend" not in {t.name for t in build_tools(repo)}
    assert [t.name for t in build_dashboard_tools(repo)] == ["get_daily_trend"]


def test_daily_trend_unknown_month():
    out = build_dashboard_tools(TenantRepo("panda-soft"))[0].invoke({"month": "2025-01"})
    assert "error" in out and "days" not in out and "2026-09" in out["months"]


# ---------- 모델 범위 전월 대비와 모르는 인자 (묶음 8-2a) ----------

def independent_mom_by_team_for_model(tenant, model, direction):
    """tools.py 를 쓰지 않고 사용 로그와 단가표로 model 범위의 팀별 전월 대비 상위 3개를 계산한다."""
    import csv
    prices = {r["model_id"]: (Decimal(r["input_usd_per_1m"]), Decimal(r["output_usd_per_1m"]))
              for r in csv.DictReader((ROOT / "data" / "prices.csv").open(encoding="utf-8"))}
    sums = {"2026-09": {}, "2026-08": {}}
    for r in csv.DictReader((ROOT / "data" / "usage" / f"{tenant}.csv").open(encoding="utf-8")):
        month = r["date"][:7]
        if month in sums and r["team"] and r["model_id"] == model:
            pin, pout = prices[model]
            cost = (int(r["input_tokens"]) * pin + int(r["output_tokens"]) * pout) / 1_000_000
            sums[month][r["team"]] = sums[month].get(r["team"], 0) + cost
    q = lambda v: str(Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    rows = []
    for team in set(sums["2026-09"]) | set(sums["2026-08"]):
        d = sums["2026-09"].get(team, 0) - sums["2026-08"].get(team, 0)
        if (direction == "increase" and d > 0) or (direction == "decrease" and d < 0):
            rows.append((d, team))
    rows.sort(key=lambda x: (-x[0] if direction == "increase" else x[0], x[1]))
    return [{"team": t, "this_usd": q(sums["2026-09"].get(t, 0)), "last_usd": q(sums["2026-08"].get(t, 0)), "delta_usd": q(d)}
            for d, t in rows[:3]]


@pytest.mark.parametrize("tenant", TENANTS)
@pytest.mark.parametrize("direction", ["increase", "decrease"])
def test_mom_scoped_to_model_matches_independent_calc(tenant, direction):
    tool = tools_for(tenant)["get_mom_change"]
    for model in sorted({r["model_id"] for r in TenantRepo(tenant).rows}):
        out = tool.invoke({"dimension": ["team"], "direction": direction, "model": model})
        got = [{k: i[k] for k in ("team", "this_usd", "last_usd", "delta_usd")} for i in out["items"]]
        assert got == independent_mom_by_team_for_model(tenant, model, direction), model
        assert out["scope"]["model"] == model and "unattributed" not in out


def test_mom_model_scope_errors():
    tool = tools_for("panda-soft")["get_mom_change"]
    assert "error" in tool.invoke({"dimension": ["team"], "model": "gpt-5"})
    out = tool.invoke({"dimension": ["model"], "model": "claude-sonnet"})
    assert "error" in out and "items" not in out
    out = tool.invoke({"dimension": ["team"], "team": "마케팅팀"})
    assert "error" in out and out["allowed"] == ["service", "model"]


@pytest.mark.parametrize("name,args", [
    ("get_cost_breakdown", {"group_by": ["team"], "model": "claude-sonnet"}),
    ("get_mom_change", {"dimension": ["team"], "modle": "claude-sonnet"}),
    ("simulate_model_swap", {"from_model": "claude-sonnet", "to_model": "claude-haiku", "quarter": "Q3"}),
])
def test_unknown_argument_is_an_error_not_ignored(name, args):
    out = json.loads(tools_for("honeybee-electronics")[name].invoke(args))
    assert "지원하지 않는 인자" in out["error"] and "allowed_args" in out
    assert not any(k in out for k in ("rows", "items", "before"))
    bad = next(k for k in args if k not in out["allowed_args"])
    assert bad in out["error"]


def test_daily_trend_rejects_unknown_argument():
    out = json.loads(build_dashboard_tools(TenantRepo("panda-soft"))[0].invoke({"month": "2026-09", "team": "마케팅팀"}))
    assert "error" in out and out["allowed_args"] == ["month"]
