# 프로젝트 규칙

무엇을 왜 만드는지는 @SERVICE.md, 실행 명세는 `~/.ouroboros/seeds/seed_ce738e162660.yaml` 을 따른다.
진행 상황과 다음 작업은 @TASKS.md 를 따른다.

## 작업 진행 방식
- 새 세션은 TASKS.md 의 결정 사항과 체크 상태, `git log --oneline -5` 로 현재 위치를 파악하고, 체크되지 않은 첫 작업부터 이어 간다
- 작업 하나를 끝내면 그 작업의 `확인:` 을 실제로 돌려 통과한 뒤에만 TASKS.md 에 체크한다. 확인을 못 했거나 막힌 작업은 체크하지 않고 그 줄 아래에 이유를 한 줄 적는다
- 범위나 결정이 바뀌면 코드보다 TASKS.md(필요하면 SERVICE.md)를 먼저 고치고 사용자 확인을 받는다
- 수정 뒤에도 결과(점수, 새로 발견한 문제)를 TASKS.md·SERVICE.md 에 반영할지 확인하고, 반영분은 같은 커밋에 넣는다
- 커밋은 작업 하나에 하나다. `확인:` 통과 후 커밋하고 TASKS.md 체크 갱신도 같은 커밋에 넣는다. 따로 커밋하면 중간 상태에서 테스트가 깨지는 작업만 묶는다

## 기술 스택
- Python, LangChain, LangGraph
- 모델은 Amazon Bedrock (ChatBedrockConverse)
- Agent 생성은 langchain.agents 의 create_agent 를 쓴다
- API 는 FastAPI, 인증은 회사별 고정 토큰(`AUTH_MODE=static`, 기본). PyJWT 로 서명한 더미 JWT 는 `AUTH_MODE=jwt` 선택 모드

## 폴더 구조 (제출 규약. 바꾸지 않는다)

src/agent.py                 메인 에이전트 그래프, 정책 판정 후 create_agent 호출
src/tools.py                 비용 집계·전월 대비·what-if 도구
src/retriever.py             공용 참고 문서 RAG (search_reference 도구)
src/api.py                   POST /query, 고정 토큰 검증(기본)·JWT 선택 모드
src/policy.py                LLM 앞 정책 판정과 거절 문구 상수
src/ui.py                    시연 화면(GET / 질문 페이지) HTML·JS 와 페이지 라우터. 인증·데이터는 다루지 않는다
data/                        더미 사용 로그, prices.csv, 사용자 매핑, 참고 문서
evaluation/                  test_queries.csv, run_eval.py, check_docs.py (채점 리포트 json 은 커밋하지 않는다)
tests/                       자격 증명 없이 도는 단위 테스트 (LLM 은 스텁)

## 주고받는 형식 (제출 규약)
- POST /query 로 받고 본문에서는 question 필드만 읽는다
- 신원은 `Authorization: Bearer <토큰>` 헤더로 받는다. 기본은 회사별 고정 토큰, JWT 선택 모드에서는 서명된 JWT. 없거나 잘못되면 401
- 답은 answer, contexts, trace 세 키로 돌려준다. 도구 결과는 contexts 에 담는다
- 대시보드 데이터는 `GET /dashboard/data?month=&scope_team=&scope_service=` 로 준다. 같은 Bearer 토큰으로 회사를 정하고, LLM 없이 도구 결과를 그대로 `kpi`·`breakdown`·`cross`·`mom`·`daily` 에 담는다. month 는 2026-09·2026-08 만, 모르는 값은 400

## 테넌트와 숫자 규칙
- 회사(테넌트)는 검증된 토큰(기본 고정 토큰, JWT 선택 모드에서는 JWT)에서만 정한다. 도구 함수는 tenant 인자를 받지 않고, 검증된 신원으로 만든 테넌트 전용 저장소로만 데이터를 읽는다
- 사용 로그에는 토큰 수만 저장한다. 실제 비용과 what-if 비용은 모두 도구가 data/prices.csv 하나로 계산한다
- LLM 은 도구가 계산한 숫자를 옮기기만 하고 직접 계산하지 않는다
- 금액은 USD 소수 둘째 자리로 계산·채점하고, 답변에는 `$X (약 N원)` 처럼 설정 파일의 고정 환율로 KRW 를 함께 쓴다
- 기본 기간은 이번 달 2026-09, 지난달 2026-08, 기준일 2026-09-30 이다

## 인-아웃 세트와 채점
- evaluation/test_queries.csv 컬럼: id, category, input, expected_traits, forbidden, expected_tools, note, user_id
- 12건: positive 5, negative 2, edge 3, guardrail 2 (guardrail 은 테넌트 격리 1건, 비밀 노출 또는 수정 요청 1건)
- 채점은 규칙 기반만 쓴다. expected_traits·forbidden·expected_tools 와 숫자 근거(answer 의 금액·원화·비율이 모두 contexts 에 있음)가 모두 통과해야 그 문항이 통과
- 합격: `python evaluation/run_eval.py --llm stub` 에서 10/12 이상, guardrail 2/2, 다른 회사 데이터 노출 0건
- `--llm bedrock` 실행 결과는 SERVICE.md 에 적는다. evaluation/eval_report_live.json 은 로컬에만 남기고 커밋하지 않는다(채점자가 요청하면 그때 올린다)

## 자주 쓰는 명령
- 서버 실행: `uvicorn src.api:app --reload`
- 시연용 JWT 발급(JWT 선택 모드): `python -m src.api issue hbe-lead-01` (1시간 뒤 만료)
- 단위 테스트: `python -m pytest -q` (한 파일만: `python -m pytest tests/test_cost_tools.py -q`)
- 채점: `python evaluation/run_eval.py --llm stub`
- 문서 확인: `python evaluation/check_docs.py`

## 코드 규칙
- 파일 하나에 한 가지 역할만 둔다
- 함수와 도구에는 한국어 docstring 을 쓴다
- 비밀 값(회사별 고정 토큰, JWT 선택 모드의 JWT 비밀키, AWS 자격 증명)은 .env 에서 읽고 코드에 적지 않는다
- 거절 문구는 src/policy.py 의 상수만 쓰고, 채점의 expected_traits 에도 같은 문자열을 쓴다

## 하지 말 것
- 요청하지 않은 파일을 새로 만들지 않는다
- 기존 파일을 통째로 다시 쓰지 않는다. 바뀐 부분만 고친다
- 두 회사 더미 데이터에 같은 USD 금액을 만들지 않는다 (누출 검사가 오탐한다). 예외: 대시보드 전용 일별 금액은 겹침 검사에서 빼고, 대시보드 누출 테스트는 다른 회사에만 있는 금액으로 검사한다
- 태그 없는 로그의 원인을 추론하지 않는다. 미귀속(Unattributed)으로 따로 보여준다. 모델 기준 집계에서는 미귀속 안에서만 모델별로 나누고 팀·서비스·기능에 배분하지 않는다
