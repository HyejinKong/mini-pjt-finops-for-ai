"""공용 참고 문서 RAG. data/reference 의 회사와 무관한 문서만 색인하는 search_reference 도구.

문서가 몇 개 안 되므로 임베딩 없이 글자 2-gram 겹침으로 순위를 매긴다(한국어 띄어쓰기에 덜 민감하다).
회사별 사용 로그나 정답 파일은 읽지 않는다.
"""

import re
from functools import lru_cache
from pathlib import Path

from langchain_core.tools import tool

REFERENCE = Path(__file__).resolve().parent.parent / "data" / "reference"
TOP_K = 3


def bigrams(text: str) -> set[str]:
    """공백을 뺀 소문자 글자 2-gram 집합."""
    s = re.sub(r"\s+", "", text.lower())
    return {s[i:i + 2] for i in range(len(s) - 1)}


@lru_cache(maxsize=1)
def load_chunks() -> tuple[dict, ...]:
    """참고 문서를 '## ' 소제목 단위 조각으로 나눈다. 조각에는 문서 제목을 붙인다."""
    chunks = []
    for path in sorted(REFERENCE.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        for part in re.split(r"\n(?=## )", text):
            body = part.strip()
            if body and body != f"# {title}":
                chunks.append({"source": path.name, "title": title, "text": body})
    return tuple(chunks)


def search(query: str, k: int = TOP_K) -> list[dict]:
    """query 와 2-gram 이 많이 겹치는 조각 k 개를 돌려준다. 긴 조각이 유리하지 않게 조각 크기의 제곱근으로 나눈다."""
    q = bigrams(query)
    scored = []
    for c in load_chunks():
        doc = bigrams(c["title"] + c["text"])
        hit = len(q & doc)
        if hit:
            scored.append((hit / len(doc) ** 0.5, c))
    scored.sort(key=lambda sc: -sc[0])
    return [c for _, c in scored[:k]]


@tool
def search_reference(query: str) -> dict:
    """회사와 무관한 공용 참고 문서(단가표, 환율, FinOps 용어·정책, 지원 질문 안내)에서 query 와 관련된 부분을 찾는다.
    '환율은 얼마로 계산해?', '미귀속이 뭐야?', 'claude-haiku 단가는?' 같은 질문에 쓴다.
    회사 비용 숫자는 들어 있지 않으므로 비용 집계에는 get_cost_breakdown, get_mom_change 를 쓴다."""
    results = search(query)
    if not results:
        return {"query": query, "results": [], "note": "관련 참고 문서를 찾지 못했습니다."}
    return {"query": query, "results": results}
