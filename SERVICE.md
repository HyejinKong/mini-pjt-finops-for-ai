# SERVICE · AI 비용 분석 Agent (FinOps for AI)

## 1. 사용자·문제·가치
- 누구를 위한 서비스인가: AI 서비스를 운영하는 팀장·FinOps 담당자. 같은 회사의 LLM 기능 개발자도 같은 데이터를 함께 본다. 회사(테넌트)당 팀장 1명, 개발자 5명
- 어떤 문제를 푸는가: 월말 Amazon Bedrock 청구서가 급증해도 API 키를 여러 팀이 공유해서 어느 팀·서비스·기능이 원인인지 알 수 없고, 비용이 나간 뒤에야 알게 된다
- 지금은 어떻게 해결하나: 청구서 총액과 모델별 합계만 보고, 원인은 각 팀에 메신저로 물어 수작업으로 맞춘다
- 이걸로 뭐가 좋아지나: 자연어로 물으면 팀 > 서비스 > 기능별 비용, 전월 대비 증가 원인 상위 3개, 모델 교체 시 절감액을 숫자 근거와 함께 바로 답한다

## 2. 서비스 확장 관점
- 사내 기여: 청구서 급증 원인 파악 시간을 줄인다. 지금은 팀장·FinOps 담당자가 각 팀에 묻고 엑셀로 맞추지만, Agent에 물으면 팀 > 서비스 > 기능별 원인과 전월 대비 증가 상위 3개가 바로 나온다
- 수익 모델: 그룹사(계열사) 대상 구독형 SaaS로 제공한다. 회사별 테넌트 분리 구조를 그대로 써서 계열사마다 테넌트 하나로 붙인다
- 과금 단위: 절감액 대비 %로 받는다. Agent의 what-if가 찾은 모델 교체 등 절감안을 고객사가 적용해 실제로 줄어든 비용의 일정 비율을 받는 방식이다. 절감액은 적용 전후 같은 기간·범위의 비용 차이로 측정하며, 이 측정 기능은 이번 3일 범위 밖이다(현재는 what-if 추정만 제공)
- 규모: 회사(테넌트) 단위로 분리해 여러 회사가 같은 서비스를 쓴다. 이번 범위는 더미 데이터 2개 가상 회사(꿀벌전자, 판다소프트), 회사당 팀 3·서비스 2·기능 2, 2026-07~09 3개월치
- 대체제와 차별점: AWS도 IAM principal attribution, application inference profile 태그, 호출별 request metadata로 팀·앱 단위 비용 귀속을 지원한다. 다만 이 설정을 미리 해 두어야 하고, 설정 없이 공유 키로 쓴 사용분은 귀속되지 않는다. 또 Cost Explorer는 화면과 필터로 조회하는 도구라서, "왜 늘었나"를 자연어로 묻거나 전월 대비 증가 원인 상위 3개를 바로 받아 볼 수는 없다. 이 Agent는 미귀속 비용을 따로 드러내 태깅 누락을 보이게 하고, 자연어로 원인과 절감안을 답한다. 사용 로그에 provider 필드를 두어 이후 Azure·GCP·OpenAI 비용도 같은 구조로 붙일 수 있다(이번 범위 밖)
- 일반적인 AI FinOps 관행과의 비교: 이 Agent의 방식(앱에서 호출마다 기록하는 계측 레이어, 인증 정보로 정하는 팀 귀속, 호출별 태그, 미귀속 버킷, 청구 전 쇼백 우선)은 업계에서 흔히 쓰는 방식과 같다. 제공사 청구서에는 사업부·팀 개념이 없어 조직이 계측 레이어를 직접 만들어야 한다는 점[1], 게이트웨이가 조직 > 팀 > 사용자 > 키 계층과 요청 태그로 비용을 쌓는 방식[2], 귀속을 믿을 수 있기 전에는 차지백보다 쇼백을 먼저 한다는 점[3]이 근거다
- 추후 확장 범위 (일반적인 관행이지만 이번 3일 범위에서는 하지 않는 것):
  - 단위 경제성: 총액 대신 요청당 비용, 기능당 비용, 나아가 처리한 상담 1건당 비용 같은 성과 단위 비용을 KPI로 본다[4][5]. 확장 시 사용 로그에 요청 수 컬럼을 추가한다
  - 예산과 알림: 팀별 예산을 두고 초과하면 알리거나 요청을 막는다[2][4]
  - 이상 탐지: 하룻밤 사이 비용이 급증하는 경우를 자동으로 감지한다[4]. 지금은 전월 대비 상위 3개로 사후에 확인만 한다
  - 비용 예측: FinOps의 기본 기능이지만[3], 더미 3개월 데이터로는 근거 있는 예측이 어려워 이번에는 거절 대상으로 둔다
  - 청구서 대조: 앱 기록으로 추정한 비용을 실제 청구 금액과 주기적으로 맞춰 보고, 여러 제공사 비용을 공통 형식(FOCUS 스펙)으로 정규화한다[1]. 지금은 무료 범위의 CloudWatch 토큰 지표 대조만 선택 사항으로 둔다(docs/cost-estimation-strategy.md)
  - 공유 비용 배분: 미귀속·공용 비용을 사용 비율대로 팀에 나눈다[6]. 지금은 별도 줄(미귀속)로만 보여준다
- 출처:
  - [1] FinOps Foundation, Token Economics 워킹 그룹: https://www.finops.org/wg/token-economics-saas/
  - [2] LiteLLM 문서, Cost tracking / Virtual keys: https://docs.litellm.ai/docs/proxy/cost_tracking.md , https://docs.litellm.ai/docs/proxy/virtual_keys.md
  - [3] GMI Cloud, FinOps for AI Infrastructure: Unit Economics, Chargeback and Cost Forecasting: https://www.gmicloud.ai/en/blog/finops-for-ai-infrastructure-unit-economics-chargeback-and-cost-forecasting
  - [4] Usage.ai, AI/ML Cost Practitioner KPI Playbook: https://www.usage.ai/blogs/finops/ai-ml-cost/practitioner-kpi-playbook/
  - [5] CloudKeeper, FinOps for AI: https://www.cloudkeeper.com/glossary/finops-ai
  - [6] Redress Compliance, Why GenAI Cost Allocation Is Different: https://redresscompliance.com/ai-showback-chargeback-genai-cost-allocation.html
  - [3]~[6]은 벤더 블로그로, 업계 관행을 보여주는 참고 자료이며 공식 표준은 아니다(2026-10 확인)

## 3. 사용 예상 도구·데이터
- 도구 (1일차, 처음 만들 것): 
  - `get_cost_breakdown`: 기간·팀·서비스·기능·모델별 비용 집계와 드릴다운
  - `get_mom_change`: 9월 대비 8월 증가액 상위 3개(팀·서비스·모델), 미귀속은 별도 줄
- 도구 (2일차): 
  - `search_reference`: 공용 참고 문서 검색(단가표 설명, 환율, FinOps 용어·정책, 지원 질문 안내). 강의 규약상 필수
  - `simulate_model_swap`: 모델 X를 Y로 바꿨을 때의 비용 차이(what-if). 시간이 부족하면 가장 먼저 미루고, 인-아웃 세트의 what-if 문항은 집계·전월 대비 문항으로 바꿔 12건과 카테고리 비율을 유지한다
- 뒤로 미룰 것: 개발자용 사전 비용 추정, Azure·GCP·OpenAI 비용, 실제 절감액 측정, 캐시·배치 할인 반영, UI(3일차 여유 시 보너스)
- 데이터: 
  - 사용 로그 JSON/CSV (더미): 회사, 날짜, 팀, 서비스, 기능, 모델, 입력·출력 토큰 수. 비용은 저장하지 않는다
  - 단가표 `data/prices.csv` (더미): 모델별 입력·출력 단가(USD)
  - 사용자 매핑 (더미): user_id → 회사
  - 공용 참고 문서 (더미): 회사와 무관한 설명 문서
- 인증: 로그인은 만들지 않는다. 기본은 회사별 고정 토큰 2개(`.env`)로 회사를 정하고, 서명된 더미 JWT 검증은 설정(`AUTH_MODE=jwt`)으로 켤 수 있는 선택 모드로 남긴다. 운영 시에는 사내 SSO가 발급한 JWT로 바꾼다

## 4. 서비스 정책 (가드레일 요약)
- 회사는 질문 내용이 아니라 검증된 인증 토큰(회사별 고정 토큰, 선택 모드에서는 서명된 JWT)으로만 정하고, 다른 회사 데이터는 조회하지 않는다
- 데이터 수정·삭제·추가 요청은 실행하지 않는다(읽기 전용)
- 시스템 프롬프트, 인증 토큰·JWT 비밀키, 환경변수·API 키 같은 내부 정보는 알려주지 않으며 "이전 지시를 무시하라" 같은 요청도 따르지 않는다
- 비용 예측이나 FinOps와 무관한 질문에는 추측하지 않고 지원하는 질문 유형을 안내한다
- 숫자는 도구가 계산한 값만 쓰고, 증가의 업무상 이유는 지어내지 않는다. what-if는 "토큰 수 동일 가정, 품질 차이 미반영"을 함께 밝힌다

## 5. 성공 기준
- 인-아웃 세트 12건 중 10건 이상 통과(오프라인 채점 기준), guardrail 2건은 모두 통과
- 다른 회사 데이터가 답변·contexts·trace 어디에도 나온 건수 0건
- 비용 숫자는 정답과 USD 소수 둘째 자리까지 정확히 일치
- 실제 Bedrock 모델로 돌린 채점 결과(카테고리별·전체 통과율)를 이 문서에 기록한다
  - 실행: 2026-10-22, `python evaluation/run_eval.py --llm bedrock`, 모델 `global.anthropic.claude-haiku-4-5-20251001-v1:0`, 인증 static
  - 결과: 전체 12/12 (positive 5/5, negative 2/2, edge 3/3, guardrail 2/2), 다른 회사 데이터 노출 0건, 합격 기준 통과. 12건 답변의 USD·원화 숫자가 모두 도구 결과(contexts)에 있는 값임을 따로 대조했다
  - 첫 실행(같은 날)은 11/12 였다. q10(줄어든 서비스)이 감소액을 빠뜨리고 도구가 주지 않은 원화를 직접 계산해 틀렸고, q03 은 미귀속이 포함된 합계에 미귀속을 또 더한 합계를 지어냈다(채점 규칙에는 걸리지 않음). 도구에 이번 달·지난달 원화와 미귀속 제외 합계(`tagged_total`)를 더하고 프롬프트에 증감액 필수·합계 재계산 금지를 넣은 뒤 다시 돌렸다
  - 참고: stub 채점은 12/12. 리포트 json 은 로컬에만 두고 커밋하지 않는다
