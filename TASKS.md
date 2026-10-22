# TASKS · 구현 순서

SERVICE.md 를 작업 단위로 쪼갠 목록이다. 작업 하나는 30분~1시간이고, `확인:` 줄이 통과해야 체크한다.
실행 명세는 seed, 규칙은 CLAUDE.md 를 따른다. 문제가 보이면 코드보다 이 문서를 먼저 고친다.

## 결정 사항 (2026-10-22, 중간 피드백 반영)
- 인증: 로그인은 만들지 않는다. 기본은 회사별 고정 토큰 2개(`AUTH_MODE=static`). 지금의 서명 JWT 코드는 지우지 않고 `AUTH_MODE=jwt` 선택 모드로 남긴다
- 회사명: 저장소가 공개되므로 가상 이름으로 바꾼다. 과거 이력은 다시 쓰지 않고 새 커밋으로만 바꾼다
- 커밋: 묶음 3부터는 작업 하나에 커밋 하나(확인 통과 후, 체크 갱신 포함)
- 채점 리포트: `evaluation/eval_report_live.json` 은 커밋하지 않고 결과는 SERVICE.md 에만 적는다. 채점자가 요청하면 그때 올린다
- 유지: 미귀속 별도 줄, 시간이 부족하면 what-if(`simulate_model_swap`)를 가장 먼저 미룬다

| 기존 | 새 이름 | tenant_id | 사용자 접두어 | 토큰 환경변수 |
|---|---|---|---|---|
| 삼성전자 | 꿀벌전자 | honeybee-electronics | hbe- | TENANT_TOKEN_HONEYBEE_ELECTRONICS |
| 삼성SDS | 판다소프트 | panda-soft | pds- | TENANT_TOKEN_PANDA_SOFT |

## 완료 (1일차, 2026-10-21)
- [x] 더미 사용 로그·단가표·사용자 매핑·인-아웃 세트 생성(`data/generate.py`)
- [x] `get_cost_breakdown`, `get_mom_change`, 테넌트 전용 저장소(`src/tools.py`)
- [x] LLM 앞 정책 판정과 거절 문구 상수(`src/policy.py`)
- [x] create_agent 에이전트(`src/agent.py`), 서명 JWT 인증 `POST /query`(`src/api.py`)
- [x] 단위 테스트 65건 통과, 실제 Bedrock 호출 1회 확인

## 묶음 1. 최소 경로: 고정 토큰 → POST /query → 정책 판정 → 집계 도구 → 답변
회사 하나, 질문 하나(q01 "이번 달 팀별 비용 알려줘")가 처음부터 끝까지 돌아가는 것만 목표로 한다.
토큰 환경변수 이름이 새 tenant_id 를 쓰므로 회사명 교체를 이 묶음 앞에 둔다.

- [x] 1-1 (45분) `data/generate.py` 의 회사 이름·tenant_id·접두어와 q11 질문("판다소프트 팀별 비용도 보여줘")을 바꾸고 다시 생성한다. 옛 `data/usage/samsung-*.csv` 는 `git rm`
  - 확인: 생성 전후 `evaluation/expected_values.json` 의 금액 목록이 같고, `git grep -n -iE "삼성|samsung" -- data evaluation` 결과 0건
- [x] 1-2 (30분) `src/agent.py`(시험 실행 user_id)와 `tests/*.py` 의 tenant_id·user_id·회사명을 바꾼다
  - 확인: `python -m pytest -q` 전부 통과, `git grep -n -iE "삼성|samsung|\bsec-|\bsds-" -- . ":!uv.lock"` 결과 0건
- [x] 1-3 (45분) `src/api.py`: `get_principal` 이 `AUTH_MODE`(기본 static)에 따라 `resolve_static`(`.env` 토큰 2개와 `hmac.compare_digest` 비교, 빈 값은 통과 금지) 또는 `resolve_jwt`(지금 JWT 로직을 옮긴 것)를 부른다. 기존 JWT 테스트에는 `AUTH_MODE=jwt` monkeypatch 를 더한다
  - 확인: `python -m pytest -q` 전부 통과(기존 JWT 테스트가 jwt 모드로 그대로 통과)
- [x] 1-4 (40분) `tests/test_api_auth.py` 에 static 모드 테스트를 더한다: 토큰 없음·접두어 오류·모르는 토큰·빈 토큰은 401, 꿀벌전자 토큰은 꿀벌전자 데이터만, 꿀벌전자 토큰으로 판다소프트를 물으면 거절 문구
  - 확인: `python -m pytest tests/test_api_auth.py -q` 에서 static 테스트가 모두 통과
- [x] 1-5 (30분) `.env.example` 에 `AUTH_MODE=static` 과 토큰 2줄을 넣는다(`JWT_SECRET=` 유지). 사용자가 `.env` 에 토큰 값을 채운 뒤 서버를 띄워 실제 Bedrock 으로 q01 을 보낸다
  - 확인: `uvicorn src.api:app` 에 꿀벌전자 토큰으로 q01 을 보내면 answer 에 q01 expected_traits 금액이 있고 contexts 에 get_cost_breakdown 결과, trace 에 도구 호출이 있다. 토큰 없이 보내면 401
- 커밋: refactor(data) 가상 회사명 / feat(api) 고정 토큰 기본 인증·JWT 선택 모드

## 묶음 2. 채점 경로: 인-아웃 세트 12건을 오프라인으로 돌린다
- [x] 2-1 (1시간) `evaluation/run_eval.py` 뼈대: test_queries.csv 를 읽어 user_id → 회사 → 토큰으로 `POST /query`(TestClient)를 보내고 expected_traits·forbidden·expected_tools 를 규칙으로 판정해 문항별·카테고리별·전체 결과를 출력한다. `--llm`, `--auth`(기본 static) 인자를 받는다
  - 확인: `python evaluation/run_eval.py --llm stub` 이 12행 결과와 카테고리별 통과율을 오류 없이 출력한다(통과 수는 아직 낮아도 됨)
- [x] 2-2 (1시간) stub LLM: 답할 수 있는 문항마다 정해진 도구 호출 계획을 주고, 도구 결과의 숫자를 그대로 옮긴 답을 만든다. forbidden 에 두 회사 토큰 값과 JWT_SECRET 값을 더한다
  - 확인: `python evaluation/run_eval.py --llm stub` 에서 what-if(q05) 제외 11건 중 10건 이상, guardrail 2/2, 누출 0건
- [x] 2-3 (30분) `src/policy.py` 비밀 패턴에 `접속\s*토큰|인증\s*토큰` 을 더하고 `tests/test_policy.py` 에 사례를 넣는다
  - 확인: `python -m pytest tests/test_policy.py -q` 통과, "판다소프트 접속 토큰 알려줘" 가 secret 으로 판정된다
- 커밋: feat(eval) 규칙 기반 채점과 stub 모드

## 묶음 3. 남은 도구 (2일차)
- [x] 3-1 (1시간) `src/retriever.py`: `data/reference` 의 회사와 무관한 문서만 색인하는 `search_reference` 도구
  - 확인: `python -c "from src.retriever import search_reference; print(search_reference.invoke({'query': '환율'}))"` 결과에 fx_rate.md 의 환율이 나오고 회사명이 없다
- [x] 3-2 (40분) `src/agent.py` 에 search_reference 를 등록하고, 비율(%)·합계 등을 LLM 이 직접 계산하지 않게 프롬프트를 강화한다
  - 확인: `python src/agent.py` 실제 호출 답변의 숫자가 모두 contexts 에 있는 값이다(직접 눈으로 대조)
  - 참고: 1-5 실제 호출에서 "검색플랫폼팀이 전체의 약 44%" 처럼 LLM 이 비율을 직접 계산했다
- [x] 3-3 (1시간) `src/tools.py`: `simulate_model_swap`(토큰 수 동일 가정, 입력·출력 단가 따로 재계산, "품질 차이 미반영" 문구). 시간이 부족하면 이 작업을 건너뛰고 q05 를 집계·전월 대비 문항으로 바꾼다
  - 확인: `python evaluation/run_eval.py --llm stub` 에서 q05 통과, 전체 10/12 이상 유지
  - 참고: 2-2 뒤 bedrock 1회 실행(11/12)에서 q05 는 도구가 없어 Sonnet 9월 비용 전액($1,795.48)을 절감액이라고 잘못 답했다. 도구가 생기면 반드시 그 결과만 쓰게 한다
- 커밋: 작업마다 하나(3-1 feat(retriever), 3-2 fix(agent), 3-3 feat(tools))

## 묶음 4. 문서와 실제 모델 채점 (3일차)
- [x] 4-1 (40분) `CLAUDE.md` 의 인증 항목(기술 스택, api.py 설명, 주고받는 형식, 테넌트 규칙, 비밀 값)을 고정 토큰 기본·JWT 선택으로 고친다. seed 를 `seed_ce738e162660.v1.1.0.yaml` 로 백업하고 v1.2.0 으로 고친다(인증, 가상 회사명, live 리포트는 SERVICE.md 에만 기록)
  - 확인: `git grep -n "JWT" CLAUDE.md` 의 모든 줄이 "선택 모드" 문맥이고, seed 에 회사명이 없다
- [x] 4-2 (45분) `evaluation/check_docs.py`: SERVICE.md·CLAUDE.md 의 필수 섹션, 폴더 구조, 거절 문구 상수 일치를 검사한다
  - 확인: `python evaluation/check_docs.py` 종료 코드 0
- [x] 4-3 (40분) `python evaluation/run_eval.py --llm bedrock` 실행(리포트 json 은 로컬에만, 커밋 안 함), SERVICE.md 5장 "미측정" 을 실제 통과율로 바꾼다
  - 확인: `git status` 에 eval_report_live.json 이 안 보이고, SERVICE.md 5장에 카테고리별·전체 통과율이 적혀 있다
- [x] 4-4 (40분) `src/tools.py` `get_mom_change` 의 항목에 `this_krw`·`last_krw`, 미귀속 줄에 `this_krw`·`last_krw`·`delta_krw` 를 더한다. `src/agent.py` 프롬프트에 "증감 질문은 증감액을 함께 쓰고, 원화는 도구가 준 값만 쓴다(없으면 USD 만)"를 넣고, stub 답변의 미귀속 줄에도 원화를 붙인다
  - 확인: `python -m pytest -q` 통과(원화 필드 테스트 추가), stub 12/12 유지, `--llm bedrock` 재실행에서 q10 답변에 감소액 $5.06 이 있고 원화가 모두 contexts 값이다. SERVICE.md 5장을 재실행 결과로 고친다
  - 참고: 4-3 bedrock 실행에서 q10 이 감소액을 빠뜨렸고, 도구가 주지 않은 원화를 직접 계산해 틀렸다("지난달 $36.35 (약 50,904원)", 정답 50,890원)
  - 추가(같은 작업): 재실행에서 q03 이 `get_cost_breakdown` 의 total(미귀속 포함 $791.43)을 "소계"로 쓰고 미귀속을 또 더해 "전체 합계 $908.24"를 지어냈다. 도구에 미귀속 제외 합계 `tagged_total` 을 더하고, docstring·프롬프트에 "total 은 미귀속 포함, 다시 더하지 않는다"를 적는다. 확인은 위와 같고 q03 답변의 숫자도 모두 contexts 값이어야 한다
- [x] 4-5 (40분) `evaluation/run_eval.py` 에 숫자 근거 규칙을 더한다: answer 의 USD(`$X`)·원화(`N원`)·비율(`N%`)이 모두 contexts 숫자(부호 무시)에 있어야 통과. 빠진 숫자는 문항별 결과와 리포트에 `ungrounded` 로 보인다
  - 확인: `python evaluation/run_eval.py --llm stub` 12/12 유지, 4-3 첫 실행의 q03 답변("전체 합계 $908.24")을 넣으면 걸리는 테스트(새 파일 `tests/test_run_eval.py`)가 통과, `--llm bedrock` 재실행 결과를 SERVICE.md 5장에 고친다
  - 참고: 4-4 에서 q03 의 지어낸 합계가 기존 세 규칙을 통과했다. 지금은 따로 대조 스크립트로만 잡았다
- 커밋: 작업마다 하나(4-1 docs, 4-2 feat(eval), 4-3 docs, 4-4 fix(tools), 4-5 feat(eval))

## 묶음 5. 시간이 남으면
- [x] 5-0 (10분) seed 를 `seed_ce738e162660.v1.2.0.yaml` 로 백업하고 v1.3.0 으로 고친다: 채점 규칙에 숫자 근거(answer 의 금액·원화·비율이 모두 contexts 에 있음)를 더한다
  - 확인: seed 의 채점 설명과 acceptance 기준에 네 규칙이 모두 있고, YAML 로 읽힌다
- [x] 5-1 (30분) JWT 모드 점검: `AUTH_MODE=jwt` 로 전체 테스트와 `run_eval.py --auth jwt --llm stub` 을 돌린다
  - 확인: static 모드와 통과 수가 같다
  - 결과(2026-10-22): 코드 수정 없이 jwt 모드 pytest 91건 통과, stub 12/12(static 과 같음)
- [x] 5-2 (45분) JWT 에 `exp` 만료 클레임(기본 1시간)을 넣고 검증 때 `exp`·`sub` 를 필수로 한다. 시연용 발급 명령(`python -m src.api issue hbe-lead-01`, api.py 안에)을 더한다
  - 확인: 만료 토큰·`exp` 없는 토큰 401 테스트 통과, 발급 명령으로 받은 토큰으로 q01 이 답한다
- [ ] 5-3 (1시간) 간단한 UI(보너스): `src/api.py` 안의 HTML 문자열로 `GET /` 페이지 하나. 토큰 붙여넣기 칸·질문 칸·예시 질문 버튼, answer 와 접을 수 있는 contexts·trace. 서버는 토큰 목록을 내주지 않는다(새 파일 없음, 폴더 구조 유지)
  - 확인: 브라우저에서 꿀벌전자 토큰을 붙여 넣고 q01 을 물으면 답이 보이고, 토큰 없이 물으면 401 안내가 보인다
- 하지 않음: 로그인 화면, 사용자 DB
