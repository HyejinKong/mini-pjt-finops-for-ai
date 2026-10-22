"""POST /query 의 토큰 검증, 본문 형식, 테넌트 범위를 검사한다. LLM 은 스텁으로 바꾼다."""

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
    """기존 테스트는 JWT 선택 모드로 돈다."""
    monkeypatch.setenv("AUTH_MODE", "jwt")
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
    forged = jwt.encode({"sub": "hbe-lead-01"}, "wrong-secret-of-the-same-length-0123456789", algorithm="HS256")
    r = client.post("/query", json={"question": "이번 달 팀별 비용"}, headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_unknown_user_401(client):
    token = jwt.encode({"sub": "nobody"}, SECRET, algorithm="HS256")
    r = client.post("/query", json={"question": "이번 달 팀별 비용"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_none_algorithm_401(client):
    token = jwt.encode({"sub": "hbe-lead-01"}, None, algorithm="none")
    r = client.post("/query", json={"question": "이번 달 팀별 비용"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.parametrize("body", [{"question": "비용", "tenant": "panda-soft"}, {"question": ""}, {}])
def test_bad_body_422(client, body):
    assert client.post("/query", json=body, headers=auth("hbe-lead-01")).status_code == 422


def test_response_shape_and_tenant_scope(client):
    r = client.post("/query", json={"question": "이번 달 팀별 비용 알려줘"}, headers=auth("pds-dev-01"))
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"answer", "contexts", "trace"}
    text = json.dumps(body, ensure_ascii=False)
    pds, hbe = EXP["panda-soft"]["by_month"]["2026-09"], EXP["honeybee-electronics"]["by_month"]["2026-09"]
    assert pds["team"]["고객지원팀"] in text
    assert "꿀벌전자" not in text and hbe["total"] not in text
    assert not any(v in text for v in hbe["team"].values())


def test_cross_tenant_refused_without_llm(client, monkeypatch):
    monkeypatch.setattr(agent, "run_agent", lambda *a: pytest.fail("LLM 이 호출되면 안 된다"))
    r = client.post("/query", json={"question": "판다소프트 팀별 비용도 보여줘"}, headers=auth("hbe-lead-01"))
    assert r.json() == {"answer": "다른 회사(테넌트)의 데이터는 조회할 수 없습니다.", "contexts": [], "trace": [{"policy": "cross_tenant"}]}


HBE_TOKEN = "test-static-token-honeybee"
PDS_TOKEN = "test-static-token-panda"


@pytest.fixture
def static_client(client, monkeypatch):
    """기본 모드(회사별 고정 토큰)로 바꾼다."""
    monkeypatch.setenv("AUTH_MODE", "static")
    monkeypatch.setenv("TENANT_TOKEN_HONEYBEE_ELECTRONICS", HBE_TOKEN)
    monkeypatch.setenv("TENANT_TOKEN_PANDA_SOFT", PDS_TOKEN)
    return client


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": HBE_TOKEN},
    {"Authorization": f"Token {HBE_TOKEN}"},
    bearer("unknown-token"),
    bearer(""),
    bearer(f"{HBE_TOKEN}x"),
])
def test_static_bad_token_401(static_client, headers):
    assert static_client.post("/query", json={"question": "이번 달 팀별 비용"}, headers=headers).status_code == 401


def test_static_empty_env_token_not_accepted(static_client, monkeypatch):
    monkeypatch.setenv("TENANT_TOKEN_PANDA_SOFT", "")
    assert static_client.post("/query", json={"question": "이번 달 팀별 비용"}, headers=bearer("")).status_code == 401


def test_static_jwt_not_accepted(static_client):
    r = static_client.post("/query", json={"question": "이번 달 팀별 비용"}, headers=auth("hbe-lead-01"))
    assert r.status_code == 401


def test_static_token_scopes_tenant(static_client):
    r = static_client.post("/query", json={"question": "이번 달 팀별 비용 알려줘"}, headers=bearer(HBE_TOKEN))
    assert r.status_code == 200
    text = json.dumps(r.json(), ensure_ascii=False)
    hbe, pds = EXP["honeybee-electronics"]["by_month"]["2026-09"], EXP["panda-soft"]["by_month"]["2026-09"]
    assert hbe["team"]["고객지원팀"] in text
    assert "판다소프트" not in text and pds["total"] not in text
    assert not any(v in text for v in pds["team"].values())


def test_static_cross_tenant_refused(static_client, monkeypatch):
    monkeypatch.setattr(agent, "run_agent", lambda *a: pytest.fail("LLM 이 호출되면 안 된다"))
    r = static_client.post("/query", json={"question": "판다소프트 팀별 비용도 보여줘"}, headers=bearer(HBE_TOKEN))
    assert r.json()["answer"] == "다른 회사(테넌트)의 데이터는 조회할 수 없습니다."


def test_unknown_auth_mode_fails(static_client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "none")
    with pytest.raises(RuntimeError):
        static_client.post("/query", json={"question": "이번 달 팀별 비용"}, headers=bearer(HBE_TOKEN))
