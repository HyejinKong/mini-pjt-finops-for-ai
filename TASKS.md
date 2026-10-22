# TASKS · 구현 순서

SERVICE.md 를 작업 단위로 쪼갠 목록이다. 작업 하나는 30분~1시간이고, `확인:` 줄이 통과해야 체크한다.
실행 명세는 seed, 규칙은 CLAUDE.md 를 따른다. 문제가 보이면 코드보다 이 문서를 먼저 고친다.

## 결정 사항 (2026-10-22, 중간 피드백 반영)
- 인증: 로그인은 만들지 않는다. 기본은 회사별 고정 토큰 2개(`AUTH_MODE=static`). 지금의 서명 JWT 코드는 지우지 않고 `AUTH_MODE=jwt` 선택 모드로 남긴다
- 회사명: 저장소가 공개되므로 가상 이름으로 바꾼다. 과거 이력은 다시 쓰지 않고 새 커밋으로만 바꾼다
- 커밋: 묶음 3부터는 작업 하나에 커밋 하나(확인 통과 후, 체크 갱신 포함)
- 채점 리포트: `evaluation/eval_report_live.json` 은 커밋하지 않고 결과는 SERVICE.md 에만 적는다. 채점자가 요청하면 그때 올린다
- 유지: 미귀속 별도 줄, 시간이 부족하면 what-if(`simulate_model_swap`)를 가장 먼저 미룬다
- 멀티 디멘전 집계(2026-10-22 추가): `group_by` 는 기준 1~2개 목록(team·service·feature·model 중 서로 다른 것). 칸 값, 기준별 소계, 전체 합계는 모두 도구가 계산한다. 미귀속은 계속 별도 줄이고, model 이 기준에 있으면 미귀속 안에서만 모델별로 나눈다(태그 없는 행도 모델은 알 수 있다)
- 대시보드(2026-10-22 추가, 묶음 7): 화면 HTML 은 새 파일 `src/ui.py` 로 분리하고 지금 `src/api.py` 의 `GET /` 페이지도 옮긴다(폴더 구조 규약에 한 줄 추가). `src/ui.py` 는 HTML·JS 문자열과 페이지 라우터만 두고 인증·데이터는 다루지 않는다. 숫자는 혼합 방식이다. 패널 숫자는 `GET /dashboard/data` 가 같은 토큰 검증을 거쳐 LLM 없이 도구를 직접 불러 만들고, LLM 요약 한 단락은 버튼을 누를 때만 `POST /query` 로 받는다. 차트는 외부 CDN 없이 인라인 SVG 로 그린다. 화면 JS 는 표시할 숫자를 계산하지 않는다(막대 길이 같은 그리기 비율만 계산). 패널은 KPI, 기준별 막대, 팀 × 모델 교차 표, 전월 대비 상위 3, 일별 추이다. 시간이 부족하면 LLM 요약(7-6), 그다음 일별 추이(7-2·7-3)를 미룬다

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
- [x] 5-3 (1시간) 간단한 UI(보너스): `src/api.py` 안의 HTML 문자열로 `GET /` 페이지 하나. 토큰 붙여넣기 칸·질문 칸·예시 질문 버튼, answer 와 접을 수 있는 contexts·trace. 서버는 토큰 목록을 내주지 않는다(새 파일 없음, 폴더 구조 유지)
  - 확인: 브라우저에서 꿀벌전자 토큰을 붙여 넣고 q01 을 물으면 답이 보이고, 토큰 없이 물으면 401 안내가 보인다
  - 결과(2026-10-22): 사용자가 브라우저에서 확인. 서버 쪽은 GET / 200(토큰 미포함), 토큰 없음 401, 꿀벌전자 토큰 q01 200 을 요청으로 재현
- [x] 5-4 (40분) 시연 페이지의 answer 를 마크다운으로 보여준다(표, 굵게, 목록, 제목, 인라인 코드, 구분선). 예시 질문 버튼에 멀티 디멘전 질문(팀 × 모델 교차 표, 팀 범위 전월 대비, 두 기준 조합 전월 대비)을 더한다. 외부 CDN 없이 `src/api.py` 의 페이지 안에 작은 변환기를 둔다. LLM 답변이라 먼저 HTML 을 이스케이프한 뒤 변환해 스크립트가 끼어들 수 없게 한다
  - 확인: q03 교차 표 답변이 브라우저에서 표로 보이고, `<script>`·`<img onerror>` 가 든 답변은 글자 그대로 보인다(node 로 변환기 단위 확인 + 사용자 브라우저 확인)
  - 결과(2026-10-22): node 로 bedrock 답변 12건·스크립트 주입·구분선 없는 표·번호 목록 사이 빈 줄을 확인했고, 사용자가 브라우저에서 표를 확인했다. 참고: Windows 에서 `uvicorn --reload` 가 변경을 못 읽고 끈 뒤에도 프로세스가 포트를 잡고 있어 옛 페이지가 나왔다. 시연 때는 `--reload` 없이 띄우고 바꾼 뒤 다시 띄운다
- 하지 않음: 로그인 화면, 사용자 DB

## 묶음 6. 멀티 디멘전 집계 (팀 × 모델 같은 교차 표)
지금은 `group_by` 가 기준 하나라 팀 × 모델 표를 한 번에 못 만들고, 팀별로 여러 번 부르면 표 합계를 LLM 이 계산하게 된다. 모델 기준 표에서는 미귀속 행의 모델이 빠진다. 시간이 부족하면 6-3 을 가장 먼저 미룬다.

- [x] 6-0 (15분) seed 를 `seed_ce738e162660.v1.3.0.yaml` 로 백업하고 v1.4.0 으로 고친다: 1~2개 기준 집계, 기준별 소계·합계는 도구가 계산, 모델 기준 미귀속은 미귀속 안에서만 모델별, 전월 대비 범위(team·service)와 두 기준 조합
  - 확인: seed 에 위 네 내용이 있고 YAML 로 읽힌다
- [x] 6-1 (1시간) `data/generate.py` 가 `tools.py` 와 독립적으로 두 기준 교차 합계(9월·8월, 서로 다른 두 기준 모든 쌍), 미귀속의 모델별 금액, 두 기준 조합·범위 지정 전월 대비 상위 3개를 `expected_values.json` 의 `multi` 에 더한다. 새 금액도 시드 탐색의 겹침 검사에 넣어 겹치지 않는 시드로 데이터를 다시 만든다. `write_test_queries` 의 q03 을 교차 표 문항으로 바꾼다(expected_traits 는 판다소프트 9월 팀 × 모델 칸 금액, forbidden 은 지금과 같은 규칙). `tests/test_run_eval.py` 의 고정 금액은 도구 결과에서 만들도록 바꾼다
  - 확인: 생성 성공(겹침 0, 미귀속 10~20%), `expected_values.json` 의 기존 키 구조는 그대로이고 `multi` 만 늘었다. `python -m pytest -q` 통과, `python evaluation/run_eval.py --llm stub` 은 q03 만 실패 가능(교차 표 stub 계획은 6-2)하고 11/12 이상·guardrail 2/2·노출 0
  - 막힘 → 해결(2026-10-22): 범위 지정 전월 대비(검색플랫폼팀 모델별 증가)에서 두 회사 증가액이 $0.04 로 겹쳐 생성기가 멈췄다. 사용자 결정으로 새 금액까지 겹치지 않는 시드로 데이터를 다시 만든다
  - 결과(2026-10-22): 생성 성공(겹침 0, 9월 미귀속 14.5%·14.8%), 기존 키 유지·`multi` 추가, 교차 합계가 단일 기준 합계와 일치, pytest 95건 통과, stub 11/12(q03 만 실패, 6-2 에서 해결)
  - 영향: 모든 금액·정답·인-아웃 세트 기대값이 바뀐다. 위 "참고" 줄과 SERVICE.md 5장의 금액은 재생성 전 데이터 기준 기록이다. bedrock 결과는 6-4 에서 새 데이터로 다시 적는다
- [x] 6-2 (1시간) `src/tools.py` `get_cost_breakdown(group_by: list, month, team, service)`: 행은 기준 이름을 필드로 갖고(`{"team": .., "model": .., "usd": .., "krw": ..}`), 두 기준이면 `subtotals`(기준별 소계)를 더한다. `total`·`tagged_total`·`unattributed` 는 지금 의미 그대로이고, model 이 기준에 있으면 `unattributed.by_model` 을 더한다. `src/agent.py` 프롬프트(교차 표 질문은 두 기준 한 번 호출, 합계·소계는 도구 값만), `evaluation/run_eval.py` stub 계획·답변(새 q03 은 `group_by=["team","model"]` 한 번 호출), 기존 테스트를 새 형식으로 고친다
  - 확인: `python -m pytest -q` 통과(교차 합계·소계·미귀속 모델별이 6-1 정답과 일치하는 테스트 추가), `python evaluation/run_eval.py --llm stub` 12/12 유지
  - 결과(2026-10-22): pytest 126건 통과(교차 표 24건·미귀속 모델별·group_by 검증 추가), stub 12/12. 참고 문서 `data/reference/supported_questions.md` 예시도 교차 표 질문으로 바꿨다
- [x] 6-3 (45분) `get_mom_change` 에 `team`·`service` 범위 인자와 1~2개 기준 `dimension` 목록을 더한다. 순위는 지금처럼 USD 증감액 기준, 미귀속은 범위를 좁히면 빠진다(집계와 같은 규칙)
  - 확인: `python -m pytest -q` 통과(범위·두 기준 전월 대비가 6-1 정답과 일치), stub 12/12 유지
  - 결과(2026-10-22): pytest 147건 통과(두 기준 전월 대비 12건·팀 범위 전월 대비 8건·오류 처리 추가), stub 12/12. 항목은 `key` 대신 기준 이름 필드를 갖는다. 지원 질문 안내에 범위 지정 예시를 더했다
- [x] 6-4 (30분) `--llm bedrock` 재실행과 교차 표 실제 질문 1회("9월 팀별·모델별 비용 표로 보여줘")
  - 확인: 재실행 10/12 이상·노출 0, 교차 표 답변의 금액·원화가 모두 contexts 값이다(숫자 근거 규칙과 같은 대조). SERVICE.md 5장을 고친다
  - 결과(2026-10-22): bedrock 12/12·노출 0, q03 교차 표와 범위 지정 전월 대비 실제 질문 모두 contexts 에 없는 숫자 0건. SERVICE.md 5장을 새 데이터 기준으로 고쳤다
- 커밋: 작업마다 하나(6-0 docs, 6-1 feat(data), 6-2 feat(tools), 6-3 feat(tools), 6-4 docs)
- 결정(2026-10-22): 인-아웃 세트의 q03 "9월 모델별 비용 알려줘" 를 "9월 팀별·모델별 비용 표로 보여줘"(판다소프트, positive)로 바꾼다. 12건·5/2/3/2 비율은 그대로다

## 묶음 7. 비용 대시보드 (추가 세션)
로그인한 회사의 데이터만 보는 한 페이지 대시보드다. 숫자는 모두 도구가 계산하고, 인-아웃 세트 12건과 채점 규칙은 바꾸지 않는다. 시간이 부족하면 7-6, 그다음 7-2·7-3 을 미룬다.

- [x] 7-0 (15분) seed 를 `seed_ce738e162660.v1.4.0.yaml` 로 백업하고 v1.5.0 으로 고친다: 대시보드 범위(패널 다섯 개, 도구 직접 호출 + 버튼으로 받는 LLM 요약, 인라인 SVG, `src/ui.py` 분리), 테넌트 격리, 화면은 숫자를 계산하지 않는다는 규칙
  - 확인: seed 에 위 내용이 있고 YAML 로 읽힌다
  - 결과(2026-10-22): constraints 에 위 내용과 미룰 순서를 넣고 폴더 규약에 `src/ui.py` 를 더했다. 옛 Streamlit 예시 문구는 지웠다. 대시보드는 지금의 UI 처럼 합격 기준(acceptance gate) 밖이라 acceptance_criteria 는 그대로다
- [ ] 7-1 (40분) `src/api.py` 의 `GET /` HTML·JS 를 `src/ui.py`(FastAPI `APIRouter`)로 옮기고 `api.py` 는 `include_router` 만 한다. 동작은 바꾸지 않는다. CLAUDE.md 폴더 구조에 `src/ui.py` 줄을 넣고 api.py 설명에서 시연 페이지를 뺀다(`check_docs.py` 는 적힌 경로가 실제로 있는지 보므로 코드 수정은 필요 없고, 파일이 생긴 이 작업에서 문서를 고친다)
  - 확인: `python -m pytest -q` 통과, 옮기기 전후 `GET /` 응답 본문이 같고(diff 0), `python evaluation/check_docs.py` 종료 코드 0
- [ ] 7-2 (40분) `data/generate.py` 가 `tools.py` 와 독립적으로 회사별 일별 합계(9월·8월, 전체와 미귀속)를 계산해 `expected_values.json` 에 `daily` 로 더한다. 새 금액도 겹침 검사(`all_amounts`)에 들어간다
  - 확인: 기존 키 구조는 그대로이고 `daily` 만 늘었다, 겹침 0. 겹치면 6-1 처럼 시드를 다시 찾고, 금액이 바뀌면 그 영향(stub·bedrock 재실행, SERVICE.md 5장)을 이 줄 아래에 적는다
- [ ] 7-3 (45분) `src/tools.py`: `get_daily_trend(month)` 는 일별 `usd`·`krw` 와 미귀속 일별 금액을 준다(회사 전체만, 범위 인자 없음). 에이전트에는 등록하지 않는다(대시보드 전용). KPI 에 쓸 값 중 도구에 없는 것(미귀속 비율, 전체 전월 대비 증감액·증감률)은 `get_cost_breakdown`·`get_mom_change` 결과에 필드로 더한다
  - 확인: `python -m pytest -q` 통과(일별 합계가 7-2 정답과 같고, 일별 합의 월 합계가 `get_cost_breakdown` total 과 같음), stub 12/12 유지
- [ ] 7-4 (45분) `src/api.py`: `GET /dashboard/data?month=2026-09&scope_team=&scope_service=` 가 `get_principal` 로 회사를 정하고 테넌트 전용 저장소의 도구를 직접 불러 `{kpi, breakdown: {team, service, model}, cross, mom: {increase, decrease}, daily}` 를 돌려준다. 범위 인자는 전월 대비 패널에만 적용한다. 테스트는 새 파일 `tests/test_dashboard.py` 에 둔다. CLAUDE.md "주고받는 형식" 에 이 엔드포인트(같은 Bearer 토큰, LLM 없이 도구 결과)를 한 줄 더한다
  - 확인: `python -m pytest tests/test_dashboard.py -q` 통과. 토큰 없음·잘못된 토큰은 401, 꿀벌전자 토큰 응답에 판다소프트 금액이 0건, 응답 숫자가 같은 인자로 부른 도구 결과와 같고, 모르는 month·team 은 400
- [ ] 7-5 (1시간) `src/ui.py`: `GET /dashboard` 페이지. 토큰 칸(`GET /` 와 같은 방식, 서버는 토큰 목록을 내주지 않음), 월 선택, KPI 카드(9월·8월 합계, 증감액·증감률, 미귀속 금액·비율), 팀·서비스·모델 막대(미귀속은 다른 색의 별도 막대), 팀 × 모델 히트맵 표(소계·합계 포함), 전월 대비 증가·감소 상위 3(범위 선택), 일별 꺾은선. 모든 글자는 이스케이프해 넣고 숫자는 응답 값을 그대로 쓴다. `GET /` 와 서로 링크한다. CLAUDE.md "자주 쓰는 명령" 에 대시보드 주소(`http://127.0.0.1:8000/dashboard`)를 더한다
  - 확인: 브라우저에서 꿀벌전자 토큰으로 다섯 패널이 보이고 KPI·표 숫자가 `/dashboard/data` 응답과 같다(사용자 브라우저 확인 + node 로 렌더 함수 단위 확인), 토큰 없이 열면 401 안내
- [ ] 7-6 (30분) 대시보드의 "요약 받기" 버튼이 정해진 질문("이번 달 비용을 전월 대비 증감과 가장 많이 늘어난 항목 3개 중심으로 요약해줘")을 `POST /query` 로 보내고, answer 를 기존 마크다운 변환기로 보여준다(자동 호출 안 함)
  - 확인: 실제 Bedrock 1회에서 요약의 금액·원화·비율이 모두 그 응답의 contexts 에 있다(숫자 근거 규칙과 같은 대조), 결과를 SERVICE.md 5장에 한 줄 적는다
- 커밋: 작업마다 하나(7-0 docs, 7-1 refactor(ui), 7-2 feat(data), 7-3 feat(tools), 7-4 feat(api), 7-5 feat(ui), 7-6 feat(ui))
- 하지 않음: 실시간 갱신, 기간 직접 입력(9월·8월만), 대시보드 숫자 내려받기, 일별 추이의 팀·서비스 범위
