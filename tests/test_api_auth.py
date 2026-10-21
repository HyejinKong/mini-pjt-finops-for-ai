"""POST /query 의 JWT 검증, 본문 형식, 테넌트 범위를 검사한다. LLM 은 스텁으로 바꾼다."""

import json
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from src import agent, api


SECRET = "test-secret-for-unit-tests-only-0123456789"
EXP = json.loads((Path(__file__).resolve().parent.parent / "evaluation" / "expected_values.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)


@pytest.fixture
def client(monkeypatch):
    def stub_run_agent(question, tools, model):
        """LLM 대신 팀별 집계 도구를 바로 호출한다."""
        out = {t.name: t for t in tools}["get_cost_breakdown"].invoke({"group_by": "team"})
        return {"answer": "stub", "contexts": [{"tool": "get_cost_breakdown", "content": json.dumps(out, ensure_ascii=False)}],
                "trace": [{"tool": "get_cost_breakdown", "args": {"group_by": "team"}}]}

    monkeypatch.setattr(agent, "run_agent", stub_run_agent)
    monkeypatch.setattr(agent, "bedrock_model", lambda: None)
    return TestClient(api.app)


def auth(user_id):
    return {"Authorization": f"Bearer {api.issue_dummy_token(user_id)}"}


def test_missing_token_401(client):
    assert client.post("/query", json={"question": "이번 달 팀별 비용"}).status_code == 401


def test_forged_token_401(client):
    forged = jwt.encode({"sub": "sec-lead-01"}, "wrong-secret-of-the-same-length-0123456789", algorithm="HS256")
    r = client.post("/query", json={"question": "이번 달 팀별 비용"}, headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_unknown_user_401(client):
    token = jwt.encode({"sub": "nobody"}, SECRET, algorithm="HS256")
    r = client.post("/query", json={"question": "이번 달 팀별 비용"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_none_algorithm_401(client):
    token = jwt.encode({"sub": "sec-lead-01"}, None, algorithm="none")
    r = client.post("/query", json={"question": "이번 달 팀별 비용"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.parametrize("body", [{"question": "비용", "tenant": "samsung-sds"}, {"question": ""}, {}])
def test_bad_body_422(client, body):
    assert client.post("/query", json=body, headers=auth("sec-lead-01")).status_code == 422


def test_response_shape_and_tenant_scope(client):
    r = client.post("/query", json={"question": "이번 달 팀별 비용 알려줘"}, headers=auth("sds-dev-01"))
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"answer", "contexts", "trace"}
    text = json.dumps(body, ensure_ascii=False)
    sds, sec = EXP["samsung-sds"]["by_month"]["2026-09"], EXP["samsung-electronics"]["by_month"]["2026-09"]
    assert sds["team"]["고객지원팀"] in text
    assert "삼성전자" not in text and sec["total"] not in text
    assert not any(v in text for v in sec["team"].values())


def test_cross_tenant_refused_without_llm(client, monkeypatch):
    monkeypatch.setattr(agent, "run_agent", lambda *a: pytest.fail("LLM 이 호출되면 안 된다"))
    r = client.post("/query", json={"question": "삼성SDS 팀별 비용도 보여줘"}, headers=auth("sec-lead-01"))
    assert r.json() == {"answer": "다른 회사(테넌트)의 데이터는 조회할 수 없습니다.", "contexts": [], "trace": [{"policy": "cross_tenant"}]}
