"""비용 집계 도구.

데이터 접근은 TenantRepo 하나로만 한다. TenantRepo 는 검증된 인증 토큰의 tenant_id 로만 만들고,
자기 회사 사용 로그 파일 하나만 연다. 도구 함수에는 tenant 인자가 없다.

금액은 1e-8 USD 단위 정수(토큰 × 센트 단가)로 정확히 합산하고,
출력할 때만 USD 소수 둘째 자리(반올림: ROUND_HALF_UP)로 바꾼다.
"""

import csv
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

DATA = Path(__file__).resolve().parent.parent / "data"
UNATTRIBUTED = "미귀속"
WHATIF_ASSUMPTION = "토큰 수 동일 가정, 품질 차이 미반영"


def load_settings() -> dict:
    """data/settings.json 을 읽는다(환율, 기본 기간 등)."""
    return json.loads((DATA / "settings.json").read_text(encoding="utf-8"))


def load_prices() -> dict:
    """모델별 (입력, 출력) 단가를 센트(per 1M tokens) 정수로 읽는다."""
    with (DATA / "prices.csv").open(encoding="utf-8") as f:
        return {
            r["model_id"]: (int(Decimal(r["input_usd_per_1m"]) * 100), int(Decimal(r["output_usd_per_1m"]) * 100))
            for r in csv.DictReader(f)
        }


def to_usd(e8: int) -> str:
    """1e-8 USD 정수를 USD 소수 둘째 자리 문자열로 바꾼다."""
    return str((Decimal(e8) / Decimal(10**8)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def to_krw(e8: int, rate: int) -> int:
    """1e-8 USD 정수를 고정 환율로 원화 정수로 바꾼다(표시용)."""
    return int((Decimal(to_usd(e8)) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def change_pct(delta_e8: int, last_e8: int) -> str:
    """증감률을 소수 한 자리 문자열로 돌려준다. 지난달이 0이면 '신규'."""
    if last_e8 == 0:
        return "신규"
    return str((Decimal(delta_e8) * 100 / Decimal(last_e8)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


class TenantRepo:
    """한 회사(테넌트)의 사용 로그만 읽는 저장소."""

    def __init__(self, tenant_id: str):
        """tenant_id 의 사용 로그 파일 하나만 연다. 다른 회사 파일은 읽지 않는다."""
        known = {t["tenant_id"] for t in json.loads((DATA / "tenants.json").read_text(encoding="utf-8"))}
        if tenant_id not in known:
            raise ValueError(f"알 수 없는 테넌트: {tenant_id}")
        path = DATA / "usage" / f"{tenant_id}.csv"
        self.prices = load_prices()
        self.settings = load_settings()
        with path.open(encoding="utf-8") as f:
            self.rows = list(csv.DictReader(f))

    def cost_e8(self, row: dict) -> int:
        """행 하나의 비용을 1e-8 USD 정수로 계산한다."""
        pin, pout = self.prices[row["model_id"]]
        return int(row["input_tokens"]) * pin + int(row["output_tokens"]) * pout

    def money(self, e8: int) -> dict:
        """금액을 USD 문자열과 원화 정수로 함께 돌려준다."""
        return {"usd": to_usd(e8), "krw": to_krw(e8, self.settings["krw_rate"])}

    def sum_by(self, month: str, key: str | tuple[str, ...], team: str | None = None,
               service: str | None = None) -> tuple[dict, int]:
        """month 비용을 key 별로 합산한다. key 가 튜플이면 그 컬럼 값들의 조합별로 합산한다.
        태그된 행 합계(dict)와 미귀속 합계를 돌려준다."""
        groups, unattributed = {}, 0
        for r in self.rows:
            if not r["date"].startswith(month):
                continue
            if not r["team"]:
                if team is None and service is None:
                    unattributed += self.cost_e8(r)
                continue
            if team is not None and r["team"] != team:
                continue
            if service is not None and r["service"] != service:
                continue
            group = tuple(r[k] for k in key) if isinstance(key, tuple) else r[key]
            groups[group] = groups.get(group, 0) + self.cost_e8(r)
        return groups, unattributed

    def unattributed_by(self, month: str, key: str) -> dict:
        """month 의 미귀속(태그 없는) 비용을 key 컬럼별로 나눈다. 모델처럼 태그와 무관한 컬럼에만 쓴다."""
        out = {}
        for r in self.rows:
            if r["date"].startswith(month) and not r["team"]:
                out[r[key]] = out.get(r[key], 0) + self.cost_e8(r)
        return out

    def scoped_rows(self, month: str, team: str | None = None, service: str | None = None,
                    feature: str | None = None) -> list[dict]:
        """month 의 행 중 범위에 맞는 것. 범위를 좁히면 태그 없는(미귀속) 행은 빠진다."""
        rows = [r for r in self.rows if r["date"].startswith(month)]
        for key, value in (("team", team), ("service", service), ("feature", feature)):
            if value is not None:
                rows = [r for r in rows if r[key] == value]
        return rows

    def names(self, key: str) -> set:
        """team, service 같은 컬럼에 실제로 있는 이름 목록."""
        return {r[key] for r in self.rows if r[key]}


GROUP_KEYS = {"team": "team", "service": "service", "feature": "feature", "model": "model_id"}


def build_tools(repo: TenantRepo) -> list:
    """repo 를 감싼 비용 도구들을 만든다. 도구는 tenant 인자를 받지 않는다."""

    @tool
    def get_cost_breakdown(
        group_by: list[Literal["team", "service", "feature", "model"]],
        month: str = "2026-09",
        team: str | None = None,
        service: str | None = None,
    ) -> dict:
        """현재 사용자 회사의 Bedrock 비용을 기준 1~2개(group_by 목록)로 집계한다.
        기준 하나면 팀별·모델별 같은 목록, 두 개면 ["team", "model"] 처럼 팀 × 모델 교차 표다.
        rows 의 각 행은 기준 이름(team, service, feature, model)을 필드로 갖는다.
        두 기준이면 subtotals 에 기준별 소계가 있다. 소계·합계는 직접 계산하지 말고 이 값을 쓴다.
        드릴다운하려면 team 이나 service 로 범위를 좁힌다. month 는 'YYYY-MM' 형식이다.
        금액은 USD(소수 둘째 자리)와 원화 환산값(krw)으로 돌려준다.
        태그가 없는 비용은 '미귀속'(unattributed)으로 따로 돌려준다. model 이 기준에 있으면
        unattributed.by_model 에 미귀속의 모델별 금액이 있다(팀·서비스·기능에는 나누지 않는다).
        total 은 미귀속을 포함한 전체 합계이고, 미귀속을 뺀 합계는 tagged_total 이다.
        '이번 달 팀별 비용', '고객지원팀 서비스별 비용', '9월 팀별·모델별 비용 표' 같은 질문에 쓴다."""
        dims = list(group_by)
        if not 1 <= len(dims) <= 2 or len(set(dims)) != len(dims):
            return {"error": "group_by 는 서로 다른 기준 1~2개 목록입니다.", "allowed": list(GROUP_KEYS)}
        if team is not None and team not in repo.names("team"):
            return {"error": f"'{team}' 팀은 이 회사 데이터에 없습니다.", "teams": sorted(repo.names("team"))}
        if service is not None and service not in repo.names("service"):
            return {"error": f"'{service}' 서비스는 이 회사 데이터에 없습니다.", "services": sorted(repo.names("service"))}
        groups, unattributed = repo.sum_by(month, tuple(GROUP_KEYS[d] for d in dims), team, service)
        rows = [{**dict(zip(dims, k)), **repo.money(v)} for k, v in sorted(groups.items(), key=lambda kv: (-kv[1], kv[0]))]
        result = {
            "period": month,
            "scope": {"team": team, "service": service},
            "group_by": dims,
            "rows": rows,
            "total": repo.money(sum(groups.values()) + unattributed),
        }
        if len(dims) == 2:
            result["subtotals"] = {}
            for i, d in enumerate(dims):
                sub = {}
                for k, v in groups.items():
                    sub[k[i]] = sub.get(k[i], 0) + v
                result["subtotals"][d] = [{d: k, **repo.money(v)} for k, v in sorted(sub.items(), key=lambda kv: (-kv[1], kv[0]))]
        if team is None and service is None:
            result["unattributed"] = {"key": UNATTRIBUTED, **repo.money(unattributed)}
            if "model" in dims:
                by_model = repo.unattributed_by(month, "model_id")
                result["unattributed"]["by_model"] = [
                    {"model": k, **repo.money(v)} for k, v in sorted(by_model.items(), key=lambda kv: (-kv[1], kv[0]))]
            result["tagged_total"] = repo.money(sum(groups.values()))
        return result

    @tool
    def get_mom_change(
        dimension: Literal["team", "service", "model"],
        direction: Literal["increase", "decrease"] = "increase",
        this_month: str = "2026-09",
        last_month: str = "2026-08",
        top_n: int = 3,
    ) -> dict:
        """지난달 대비 이번 달 비용이 가장 많이 늘어난(direction='increase') 또는 줄어든(direction='decrease') 상위 항목을 돌려준다.
        순위는 USD 증감액 기준이며 증감률(pct_or_new)은 소수 한 자리다. 지난달 비용이 0인 항목은 '신규'로 표시한다.
        미귀속 비용은 순위에서 빼고 unattributed 로 따로 돌려준다.
        증가의 업무상 이유는 데이터에 없으므로 추측하지 않는다.
        '왜 늘었어', '전월 대비 증가 원인', '줄어든 서비스' 같은 질문에 쓴다."""
        key = GROUP_KEYS[dimension]
        this, this_un = repo.sum_by(this_month, key)
        last, last_un = repo.sum_by(last_month, key)
        items = []
        for k in set(this) | set(last):
            d = this.get(k, 0) - last.get(k, 0)
            if (direction == "increase" and d > 0) or (direction == "decrease" and d < 0):
                items.append((d, k))
        items.sort(key=lambda x: x[0], reverse=(direction == "increase"))
        rate = repo.settings["krw_rate"]
        return {
            "this_month": this_month,
            "last_month": last_month,
            "dimension": dimension,
            "direction": direction,
            "items": [
                {
                    "key": k,
                    "this_usd": to_usd(this.get(k, 0)),
                    "this_krw": to_krw(this.get(k, 0), rate),
                    "last_usd": to_usd(last.get(k, 0)),
                    "last_krw": to_krw(last.get(k, 0), rate),
                    "delta_usd": to_usd(d),
                    "delta_krw": to_krw(d, rate),
                    "pct_or_new": change_pct(d, last.get(k, 0)),
                }
                for d, k in items[:top_n]
            ],
            "unattributed": {
                "key": UNATTRIBUTED,
                "this_usd": to_usd(this_un),
                "this_krw": to_krw(this_un, rate),
                "last_usd": to_usd(last_un),
                "last_krw": to_krw(last_un, rate),
                "delta_usd": to_usd(this_un - last_un),
                "delta_krw": to_krw(this_un - last_un, rate),
            },
        }

    @tool
    def simulate_model_swap(
        from_model: str,
        to_model: str,
        month: str = "2026-09",
        team: str | None = None,
        service: str | None = None,
        feature: str | None = None,
    ) -> dict:
        """모델 from_model 로 쓴 사용분을 to_model 로 바꿨다면 비용이 어떻게 달라지는지 계산한다(what-if).
        같은 기간·범위의 입력·출력 토큰 수를 그대로 두고 to_model 의 입력·출력 단가로 다시 계산한다.
        범위는 회사 전체(기본) 또는 team, service, feature 로 좁힌다. month 는 'YYYY-MM' 형식이다.
        change.kind 가 saving 이면 절감, increase 면 비용 증가다. 답에는 assumption 문구를 함께 쓴다.
        'claude-sonnet 을 claude-haiku 로 바꾸면 얼마나 줄어?' 같은 질문에 쓴다."""
        scope = {"team": team, "service": service, "feature": feature}
        base = {"period": month, "scope": scope, "from_model": from_model, "to_model": to_model,
                "assumption": WHATIF_ASSUMPTION}
        unknown = [m for m in (from_model, to_model) if m not in repo.prices]
        if unknown:
            return {**base, "error": f"단가표에 없는 모델입니다: {', '.join(unknown)}", "models": sorted(repo.prices)}
        for key, value in scope.items():
            if value is not None and value not in repo.names(key):
                return {**base, "error": f"'{value}' 은(는) 이 회사 데이터에 없는 {key} 입니다.",
                        f"{key}s": sorted(repo.names(key))}
        if from_model == to_model:
            return {**base, "kind": "no_change", "message": "같은 모델이라 비용 변화가 없습니다."}
        rows = repo.scoped_rows(month, team, service, feature)
        used = [r for r in rows if r["model_id"] == from_model]
        if not used:
            return {**base, "kind": "no_usage", "message": f"이 범위에서 {from_model} 사용분이 없어 절감액은 $0.00 입니다.",
                    "models_in_scope": sorted({r["model_id"] for r in rows})}
        inp = sum(int(r["input_tokens"]) for r in used)
        out = sum(int(r["output_tokens"]) for r in used)
        before = sum(repo.cost_e8(r) for r in used)
        to_in, to_out = repo.prices[to_model]
        after = inp * to_in + out * to_out
        kind = "saving" if after < before else ("increase" if after > before else "no_change")
        return {
            **base,
            "input_tokens": inp,
            "output_tokens": out,
            "before": repo.money(before),
            "after": repo.money(after),
            "change": {"kind": kind, **repo.money(abs(before - after))},
        }

    return [get_cost_breakdown, get_mom_change, simulate_model_swap]
