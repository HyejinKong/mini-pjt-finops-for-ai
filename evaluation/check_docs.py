"""제출 문서(SERVICE.md, CLAUDE.md)가 규약을 지키는지 규칙으로 검사한다.

검사 항목:
  - SERVICE.md 1~5장, CLAUDE.md 필수 섹션이 있는지
  - CLAUDE.md 폴더 구조에 적힌 경로와 evaluation 파일이 실제로 있는지
  - 인-아웃 세트의 거절 문구가 src/policy.py 상수와 글자 그대로 같은지

실행:
  python evaluation/check_docs.py    (모두 통과하면 종료 코드 0)
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.policy import REFUSALS

SERVICE = ROOT / "SERVICE.md"
CLAUDE = ROOT / "CLAUDE.md"
QUERIES = ROOT / "evaluation" / "test_queries.csv"

SERVICE_SECTIONS = [
    "## 1. 사용자·문제·가치",
    "## 2. 서비스 확장 관점",
    "## 3. 사용 예상 도구·데이터",
    "## 4. 서비스 정책",
    "## 5. 성공 기준",
]
CLAUDE_SECTIONS = [
    "## 기술 스택",
    "## 폴더 구조",
    "## 주고받는 형식",
    "## 테넌트와 숫자 규칙",
    "## 인-아웃 세트와 채점",
    "## 코드 규칙",
]


def headings(text: str) -> list[str]:
    """마크다운 문서의 ## 제목 줄 목록을 돌려준다."""
    return [line.strip() for line in text.splitlines() if line.startswith("## ")]


def check_sections(name: str, text: str, required: list[str]) -> list[str]:
    """필수 섹션 제목(접두어 일치)이 모두 있는지 검사하고 오류 목록을 돌려준다."""
    found = headings(text)
    return [f"{name}: 섹션 없음 '{r}'" for r in required if not any(h.startswith(r) for h in found)]


def section_body(text: str, title: str) -> str:
    """title 로 시작하는 ## 섹션의 본문(다음 ## 전까지)을 돌려준다."""
    match = re.search(rf"^{re.escape(title)}.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def check_folder_structure(text: str) -> list[str]:
    """CLAUDE.md 폴더 구조의 경로와 거기 적힌 evaluation 파일이 실제로 있는지 검사한다."""
    errors = []
    body = section_body(text, "## 폴더 구조")
    entries = re.findall(r"^(\S+)\s{2,}(.*)$", body, re.M)
    if not entries:
        return ["CLAUDE.md: 폴더 구조 항목을 찾지 못함"]
    for path, desc in entries:
        if not (ROOT / path).exists():
            errors.append(f"CLAUDE.md 폴더 구조: 없는 경로 '{path}'")
        if path.endswith("/"):
            for name in re.findall(r"[\w.-]+\.(?:py|csv)", desc):
                if not (ROOT / path / name).exists():
                    errors.append(f"CLAUDE.md 폴더 구조: 없는 파일 '{path}{name}'")
    return errors


def refusal_texts() -> set[str]:
    """채점에 쓸 수 있는 거절 문구: 상수 전체와 각 상수의 첫 문장."""
    texts = set()
    for value in REFUSALS.values():
        texts.add(value)
        texts.add(value.split(". ")[0].rstrip(".") + ".")
    return texts


def check_refusals() -> list[str]:
    """인-아웃 세트의 거절 문구가 policy.py 상수와 같은지, guardrail 문항이 상수를 쓰는지 검사한다."""
    errors = []
    allowed = refusal_texts()
    with QUERIES.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        traits = [t.strip() for t in row["expected_traits"].split(";") if t.strip()]
        refusals = [t for t in traits if t.endswith("습니다.")]
        for t in refusals:
            if t not in allowed:
                errors.append(f"{row['id']}: 거절 문구가 policy.py 상수와 다름 '{t}'")
        if row["category"] == "guardrail" and not refusals:
            errors.append(f"{row['id']}: guardrail 문항에 거절 문구 상수가 없음")
    return errors


def main() -> int:
    """모든 검사를 돌려 결과를 출력하고, 오류가 없으면 0 을 돌려준다."""
    service = SERVICE.read_text(encoding="utf-8")
    claude = CLAUDE.read_text(encoding="utf-8")
    errors = (
        check_sections("SERVICE.md", service, SERVICE_SECTIONS)
        + check_sections("CLAUDE.md", claude, CLAUDE_SECTIONS)
        + check_folder_structure(claude)
        + check_refusals()
    )
    if "미측정" in section_body(service, "## 5. 성공 기준"):
        print("경고: SERVICE.md 5장의 실제 Bedrock 채점 결과가 아직 '미측정'")
    for e in errors:
        print("오류:", e)
    print("문서 검사:", "통과" if not errors else f"실패 {len(errors)}건")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
