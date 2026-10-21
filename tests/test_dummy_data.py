"""더미 데이터의 모양과 의도한 패턴을 검사한다."""

import csv
import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TENANTS = ["samsung-electronics", "samsung-sds"]
FIELDS = ["provider", "date", "team", "service", "feature", "model_id", "input_tokens", "output_tokens"]


def rows(tenant):
    """회사 하나의 사용 로그 행."""
    with (DATA / "usage" / f"{tenant}.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def expected():
    """생성기가 고정한 정답값."""
    return json.loads((ROOT / "evaluation" / "expected_values.json").read_text(encoding="utf-8"))


def test_two_tenants_and_users():
    tenants = json.loads((DATA / "tenants.json").read_text(encoding="utf-8"))
    assert [t["tenant_id"] for t in tenants] == TENANTS
    users = json.loads((DATA / "users.json").read_text(encoding="utf-8"))
    for t in TENANTS:
        roles = [u["role"] for u in users if u["tenant_id"] == t]
        assert roles.count("team_lead") == 1 and roles.count("developer") == 5


def test_columns_dates_and_hierarchy():
    hierarchies = []
    for t in TENANTS:
        r = rows(t)
        assert list(r[0].keys()) == FIELDS
        assert all(x["provider"] == "aws-bedrock" for x in r)
        assert len({x["date"] for x in r}) == 92
        assert min(x["date"] for x in r) == "2026-07-01" and max(x["date"] for x in r) == "2026-09-30"
        tagged = {(x["team"], x["service"], x["feature"]) for x in r if x["team"]}
        assert len({h[0] for h in tagged}) == 3 and len({h[1] for h in tagged}) == 6 and len(tagged) == 12
        hierarchies.append(tagged)
    assert hierarchies[0] == hierarchies[1]


def test_intentional_patterns():
    exp = expected()
    for t in TENANTS:
        e, r = exp[t], rows(t)
        p = e["patterns"]
        by_month = lambda m, f: sum(int(x["input_tokens"]) for x in r if x["feature"] == f and x["date"].startswith(m))
        assert by_month("2026-07", p["new"]) == 0 and by_month("2026-08", p["new"]) == 0 and by_month("2026-09", p["new"]) > 0
        assert by_month("2026-09", p["spike"]) > 2.5 * by_month("2026-08", p["spike"])
        assert by_month("2026-09", p["decline"]) < 0.5 * by_month("2026-08", p["decline"])
        assert any(i["pct_or_new"] == "신규" for i in e["mom_increase"]["model_id"])
        for m in ("2026-08", "2026-09"):
            share = Decimal(e["by_month"][m]["unattributed"]) / Decimal(e["by_month"][m]["total"])
            assert Decimal("0.10") <= share <= Decimal("0.20")


def test_no_shared_amounts_between_tenants():
    exp = expected()

    def amounts(v, acc):
        if isinstance(v, dict):
            for x in v.values():
                amounts(x, acc)
        elif isinstance(v, list):
            for x in v:
                amounts(x, acc)
        elif isinstance(v, str) and v.replace("-", "").replace(".", "").isdigit() and "." in v:
            if Decimal(v) != 0:
                acc.add(str(abs(Decimal(v))))
        return acc

    a = amounts(exp["samsung-electronics"]["by_month"], set())
    b = amounts(exp["samsung-sds"]["by_month"], set())
    assert not (a & b)


def test_generator_is_deterministic():
    targets = [DATA / "usage" / f"{t}.csv" for t in TENANTS] + [ROOT / "evaluation" / "expected_values.json"]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in targets]
    subprocess.run([sys.executable, str(DATA / "generate.py")], check=True, capture_output=True)
    after = [hashlib.sha256(p.read_bytes()).hexdigest() for p in targets]
    assert before == after
