# AI 사용량 기록과 비용 산정 전략

이 문서는 이 Agent가 실제로 쓴 Amazon Bedrock 사용량을 어떻게 기록하고 비용을 어떻게 산정하는지 정한다.
미니 프로젝트 범위에서는 **앱이 직접 기록하는 방식만** 쓰고, 추가 AWS API 호출이나 추가 과금이 생기는 방법은 쓰지 않는다.

## 1. 결론
- 이 앱이 Bedrock을 부를 때마다 응답에 들어 있는 토큰 사용량을 로컬 파일에 기록한다
- 비용은 기록된 토큰 수에 `data/prices.csv` 단가를 곱해 앱 안에서 계산한다
- 기록 형식은 더미 사용 로그와 같은 컬럼을 쓴다. 그래서 기존 도구(get_cost_breakdown, get_mom_change)를 고치지 않고 실제 기록으로 바꿔 읽을 수 있다

## 2. 왜 앱에서 기록하나
| 방법 | 추가 AWS 호출 | 과금 | 과거 데이터 | 팀·기능 귀속 | 이번 범위 |
|---|---|---|---|---|---|
| **앱에서 직접 기록** | 없음 | 없음 | 없음(기록 시작 이후) | 됨(앱이 호출자를 앎) | **채택** |
| CloudWatch 지표 (`GetMetricStatistics`) | 있음 | 무료 티어 안이면 없음 | 있음 | 안 됨(모델 단위) | 검증용 선택 사항 |
| Model invocation log | 있음(설정, 조회) | 저장·조회 비용 가능 | 없음(켠 이후) | request metadata를 붙이면 됨 | 범위 밖 |
| Cost Explorer / CUR 2.0 | 있음 | 조회당 과금 | 있음 | 태그·IAM 설정 시 | 범위 밖 |

앱이 직접 기록하는 방식은 여러 팀이 공유 키를 쓰는 문제를 실제로 푸는 방식과도 같다. 공유 키 앞단의 게이트웨이에서 호출자별로 계량하는 구조다.
대신 **이 앱을 거친 호출만** 잡힌다. 같은 계정에서 다른 경로로 쓴 Bedrock 사용량은 포함되지 않는다.

## 3. 무엇을 기록하나
Bedrock 응답의 사용량 정보를 그대로 쓴다. LangChain에서는 각 `AIMessage.usage_metadata`에 들어 있다.
한 질문에 LLM 호출이 여러 번 일어날 수 있으므로(도구 호출 → 결과 해석) **LLM 호출 1번 = 기록 1행**으로 남긴다.

| 컬럼 | 내용 | 출처 |
|---|---|---|
| provider | `aws-bedrock` | 고정값 |
| date | 호출 날짜 `YYYY-MM-DD` | 서버 시각 |
| team | 호출한 사용자의 팀 | users.json |
| service | `finops-agent` | 고정값 |
| feature | 질문 경로(예: `cost_breakdown`, `mom_change`, `answer`) | 해당 LLM 호출 직후의 도구 호출 |
| model_id | 실제 Bedrock 모델 ID | 설정 `BEDROCK_MODEL_ID` |
| input_tokens | 입력 토큰 | `usage_metadata.input_tokens` |
| output_tokens | 출력 토큰 | `usage_metadata.output_tokens` |
| timestamp, user_id, request_id | 추적용 | 서버 |
| cache_read_tokens, cache_write_tokens | 캐시 토큰(기록만, 비용 산정 제외) | `usage_metadata.input_token_details` |

- 앞의 8개 컬럼은 더미 사용 로그와 같다. 뒤의 추적용 컬럼은 도구가 읽지 않는다
- 질문과 답변 본문은 기록하지 않는다. 비용 산정에 필요 없고 민감 정보가 남기 때문이다
- 저장 위치: `data/usage_live/<tenant_id>.csv`. 회사별 파일로 나눠 더미와 같은 방식으로 격리한다. 이 폴더는 커밋하지 않는다
- 정책 게이트에서 거절한 질문은 LLM을 부르지 않으므로 기록할 것도 없고 비용도 0이다

## 4. 비용 산정 방법
- 산식: `비용 = 입력 토큰 × 입력 단가 / 1,000,000 + 출력 토큰 × 출력 단가 / 1,000,000`
- 계산: 단가를 센트 정수로 바꿔 정수로 합산하고, 보여줄 때만 USD 소수 둘째 자리로 반올림한다(더미 데이터와 같은 규칙)
- 원화: `data/settings.json`의 고정 환율(1 USD = 1,400 KRW)로 표시만 한다
- 단가표: 실제 호출에 쓰는 모델 ID의 단가 행을 `data/prices.csv`에 추가한다. 행마다 단가 기준일을 함께 적는다
  - 예: `global.anthropic.claude-haiku-4-5-20251001-v1:0` 입력 $1.00 / 출력 $5.00 per 1M (2026-10 기준, 공시가)
  - 더미 단가표의 모델 이름(`claude-sonnet`, `claude-haiku`, `nova-pro`, `nova-lite`)은 실제 모델 ID가 아니므로, 단가가 같더라도 실제 기록용 행은 실제 모델 ID로 따로 둔다. 더미 단가는 2026-10 공시가(Sonnet 4.5 3.00/15.00, Haiku 4.5 1.00/5.00, Nova Pro 0.80/3.20, Nova Lite 0.06/0.24)에 맞췄다
- 단가표에 없는 모델: 토큰은 기록하고, 비용은 "단가 없음"으로 표시해 합계에서 뺀다. 0으로 계산하지 않는다

## 5. 정확도와 한계
이 방식으로 계산한 금액은 **추정 비용**이며 청구서 금액과 다를 수 있다.

| 차이 원인 | 영향 | 이번 처리 |
|---|---|---|
| 프롬프트 캐시 할인(읽기 약 0.1배, 쓰기 약 1.25배) | 캐시를 쓰면 실제가 더 쌈 | 토큰만 기록, 비용 산정 제외 |
| 리전 전용 엔드포인트 할증(약 10%) | global 프로파일은 할증 없음 | global 프로파일 사용 |
| 배치·Flex·Priority 요금 | on-demand만 사용 | 해당 없음 |
| 실패한 호출, 재시도 | 앱 기록과 청구가 어긋날 수 있음 | 성공 응답만 기록 |
| 다른 경로의 Bedrock 사용 | 계정 전체보다 적게 잡힘 | 이 앱 사용량만 다룬다고 명시 |
| 공시 단가 변경 | 단가표가 낡으면 오차 | 단가 행에 기준일 기록 |

## 6. 검증 (선택 사항)
필요할 때만 CloudWatch `GetMetricStatistics`로 같은 기간·모델의 `InputTokenCount`, `OutputTokenCount`를 조회해 앱 기록과 맞춰 본다.
무료 티어(월 100만 API 요청) 안에서 하며, `GetMetricData`, Logs Insights, Cost Explorer는 과금되므로 쓰지 않는다.

## 7. 구현 계획 (2일차)
1. `src/agent.py`의 `run_agent`에서 결과 메시지 중 `AIMessage.usage_metadata`를 모아 기록 함수에 넘긴다
2. 기록 함수는 회사별 CSV에 행을 덧붙인다(파일 하나에 한 가지 역할 원칙에 따라 기록 전용 모듈로 둔다)
3. `data/prices.csv`에 실제 모델 ID 단가 행과 기준일을 추가한다
4. `TenantRepo`가 더미 로그(`data/usage/`)와 실제 기록(`data/usage_live/`) 중 무엇을 읽을지 설정으로 고르게 한다. 기본값은 더미이며, 채점은 항상 더미로 한다
5. 테스트: 스텁 LLM 응답의 사용량으로 기록 행과 계산된 비용을 검증한다. 실제 Bedrock 호출 없이 돈다

## 8. 범위 밖 (이후 확장)
일반적인 AI FinOps 관행 중 이번에 하지 않는 항목(단위 경제성, 예산·알림, 이상 탐지, 비용 예측, 청구서 대조, 공유 비용 배분)과 출처는 SERVICE.md 2장 "추후 확장 범위"에 정리했다. 아래는 이 문서의 기록·산정 방식과 직접 관련된 확장이다.

- 계정 전체 사용량: model invocation log와 호출별 request metadata(team, service, feature)를 쓴다
- 청구 금액 기준 귀속: IAM principal attribution이나 application inference profile 태그와 Cost Explorer / CUR 2.0을 쓴다
- 실제 절감액 측정(과금 모델의 근거): 절감안 적용 전후로 같은 기간·범위의 기록 비용을 비교한다
