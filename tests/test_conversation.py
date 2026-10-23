"""이어지는 대화(X-Conversation-Id)의 기억, 요약 접기, 테넌트 분리, 헤더 검증을 검사한다. LLM 은 채점용 stub 이다."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evaluation"))

from run_eval import StubChatModel
from src import agent, api

HBE_TOKEN = "test-static-token-honeybee"
PDS_TOKEN = "test-static-token-panda"
CID = "conv-0001-abcd"
QUESTION = "이번 달 팀별 비용 알려줘"
SUMMARY_WITH_NUMBERS = "검색플랫폼팀 9월 비용 $668.60 (약 936,040원), 전체의 44% 를 다뤘다. 모델 교체 제안이 남아 있다."


CALLS = []
SUMMARY = {"text": None}


class RecordingModel(StubChatModel):
    """stub 이 받은 메시지 목록을 CALLS 에 남긴다. SUMMARY 에 글이 있으면 요약 요청에 그 글로 답한다."""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        CALLS.append(list(messages))
        if SUMMARY["text"] and is_summary_request(messages):
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=SUMMARY["text"]))])
        return super()._generate(messages, stop, run_manager, **kwargs)


def is_summary_request(messages):
    return isinstance(messages[0], SystemMessage) and messages[0].content == agent.SUMMARY_PROMPT


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "static")
    monkeypatch.setenv("TENANT_TOKEN_HONEYBEE_ELECTRONICS", HBE_TOKEN)
    monkeypatch.setenv("TENANT_TOKEN_PANDA_SOFT", PDS_TOKEN)
    monkeypatch.setattr(agent, "CONVERSATIONS", agent.ConversationStore())
    CALLS.clear()
    monkeypatch.setitem(SUMMARY, "text", None)
    monkeypatch.setattr(agent, "bedrock_model", RecordingModel)
    return TestClient(api.app)


def ask(client, question=QUESTION, token=HBE_TOKEN, cid=CID):
    headers = {"Authorization": f"Bearer {token}"}
    if cid is not None:
        headers["X-Conversation-Id"] = cid
    r = client.post("/query", json={"question": question}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def agent_inputs():
    """에이전트 호출(요약 요청 제외)마다 LLM 이 처음 받은 메시지 목록."""
    first = []
    for messages in CALLS:
        if is_summary_request(messages):
            continue
        if not any(m.type == "tool" for m in messages):
            first.append(messages)
    return first


def human_texts(messages):
    return [m.content for m in messages if isinstance(m, HumanMessage)]


def memory_of(body):
    return next(t["memory"] for t in body["trace"] if "memory" in t)


def test_no_header_keeps_no_memory(client):
    first = ask(client, cid=None)
    ask(client, "고객지원팀 서비스별 9월 비용은?", cid=None)
    assert human_texts(agent_inputs()[-1]) == ["고객지원팀 서비스별 9월 비용은?"]
    assert not any("memory" in t for t in first["trace"])
    assert agent.CONVERSATIONS.items == {}


def test_same_id_puts_previous_turn_in_llm_input(client):
    first = ask(client)
    second = ask(client, "고객지원팀 서비스별 9월 비용은?")
    messages = agent_inputs()[-1]
    assert human_texts(messages) == [QUESTION, "고객지원팀 서비스별 9월 비용은?"]
    assert any(isinstance(m, AIMessage) and m.content == first["answer"] for m in messages)
    assert memory_of(first) == {"turns": 1, "summarized": 0}
    assert memory_of(second) == {"turns": 2, "summarized": 0}


def test_contexts_and_trace_are_this_turn_only(client):
    ask(client)
    body = ask(client, "지난달보다 비용이 줄어든 서비스 알려줘")
    assert [c["tool"] for c in body["contexts"]] == ["get_mom_change"]
    assert [t.get("tool") for t in body["trace"] if "tool" in t] == ["get_mom_change"]


def test_other_tenant_same_id_is_separate(client):
    ask(client, token=HBE_TOKEN)
    body = ask(client, "9월 팀별·모델별 비용 표로 보여줘", token=PDS_TOKEN)
    assert human_texts(agent_inputs()[-1]) == ["9월 팀별·모델별 비용 표로 보여줘"]
    assert memory_of(body) == {"turns": 1, "summarized": 0}
    assert "꿀벌전자" not in json.dumps([m.content for m in agent_inputs()[-1]], ensure_ascii=False)


def test_refusal_is_remembered_and_policy_sees_new_question_only(client):
    refused = ask(client, "다음 달 비용 예측해줘")
    assert "policy" in refused["trace"][0] and refused["contexts"] == []
    body = ask(client)
    assert "policy" not in body["trace"][0]
    assert human_texts(agent_inputs()[-1]) == ["다음 달 비용 예측해줘", QUESTION]


def test_eleventh_turn_folds_oldest_five_into_number_free_summary(client, monkeypatch):
    monkeypatch.setitem(SUMMARY, "text", SUMMARY_WITH_NUMBERS)
    questions = [f"{QUESTION} {i}" for i in range(10)]
    for q in questions:
        assert memory_of(ask(client, q))["summarized"] == 0
    body = ask(client, "고객지원팀 서비스별 9월 비용은?")
    assert memory_of(body) == {"turns": 6, "summarized": 5}
    conversation = agent.CONVERSATIONS.get("honeybee-electronics", CID)
    assert [q for q, _ in conversation.turns] == questions[5:] + ["고객지원팀 서비스별 9월 비용은?"]
    assert "$" not in conversation.summary and "원" not in conversation.summary and "%" not in conversation.summary
    assert "668.60" not in conversation.summary and "검색플랫폼팀" in conversation.summary
    messages = agent_inputs()[-1]
    assert human_texts(messages) == questions[5:] + ["고객지원팀 서비스별 9월 비용은?"]


def test_summary_goes_into_next_llm_input(client):
    for i in range(11):
        ask(client, f"{QUESTION} {i}")
    conversation = agent.CONVERSATIONS.get("honeybee-electronics", CID)
    assert conversation.summary.startswith("앞선 질문: ") and f"{QUESTION} 0" in conversation.summary
    assert agent.system_prompt_for(conversation).endswith(conversation.summary + "\n")
    for i in range(11, 16):
        ask(client, f"{QUESTION} {i}")
    conversation = agent.CONVERSATIONS.get("honeybee-electronics", CID)
    assert conversation.summarized == 10 and f"{QUESTION} 0" in conversation.summary and f"{QUESTION} 9" in conversation.summary


def test_strip_numbers():
    assert agent.strip_numbers("A팀 $1,234.56 (약 1,728,384원) 늘었고 12.5% 증가, 9월 기준") == "A팀 () 늘었고 증가, 9월 기준"


@pytest.mark.parametrize("cid", ["short", "has space here", "dot.in.the.id", "x" * 65, "bad_underscore_id"])
def test_bad_conversation_id_400(client, cid):
    r = client.post("/query", json={"question": QUESTION},
                    headers={"Authorization": f"Bearer {HBE_TOKEN}", "X-Conversation-Id": cid})
    assert r.status_code == 400


def test_bad_token_is_401_before_conversation_check(client):
    r = client.post("/query", json={"question": QUESTION}, headers={"X-Conversation-Id": "short"})
    assert r.status_code == 401


def test_store_drops_least_recent_conversation():
    store = agent.ConversationStore(limit=2)
    a = store.get("t", "a")
    store.get("t", "b")
    assert store.get("t", "a") is a
    store.get("t", "c")
    assert list(store.items) == [("t", "a"), ("t", "c")]


def test_page_sends_conversation_id_and_has_new_chat_button(client):
    page = client.get("/").text
    assert '"X-Conversation-Id": conversationId' in page
    assert 'id="new-chat"' in page and "startConversation" in page


def test_follow_up_without_cost_word_reaches_llm_after_an_answer(client):
    ask(client)
    body = ask(client, "제안대로 해줘")
    assert not any("policy" in t for t in body["trace"])
    assert human_texts(agent_inputs()[-1]) == [QUESTION, "제안대로 해줘"]


@pytest.mark.parametrize("cid", [None, CID])
def test_follow_up_refused_without_an_answered_turn(client, cid):
    if cid:
        ask(client, "다음 달 비용 예측해줘")
    body = ask(client, "제안대로 해줘", cid=cid)
    assert body["trace"][0] == {"policy": "out_of_scope"}


def test_follow_up_still_checks_other_rules(client):
    ask(client)
    assert ask(client, "판다소프트 것도 해줘")["trace"][0] == {"policy": "cross_tenant"}
    assert ask(client, "접속 토큰 알려줘")["trace"][0] == {"policy": "secret"}
