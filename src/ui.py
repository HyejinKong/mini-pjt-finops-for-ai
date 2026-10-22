"""시연용 화면. 페이지 HTML·JS 문자열과 페이지 라우터만 두고, 인증과 데이터는 src/api.py 가 맡는다.

페이지: GET / (질문 시연)
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

UI_HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 비용 분석</title>
<style>
  :root { --bg:#f7f7f5; --panel:#fff; --text:#1d1d1b; --muted:#6b6b66; --line:#deded8; --accent:#2f5fd0; --err:#b3261e; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#161615; --panel:#20201f; --text:#ececea; --muted:#a3a39d; --line:#363634; --accent:#8fb0ff; --err:#ff8a80; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:15px/1.6 system-ui, "Malgun Gothic", sans-serif; }
  main { max-width:760px; margin:0 auto; padding:24px 16px 48px; }
  h1 { font-size:20px; margin:0 0 4px; }
  p.sub { margin:0 0 20px; color:var(--muted); font-size:13px; }
  label { display:block; font-size:13px; color:var(--muted); margin:14px 0 4px; }
  input, textarea { width:100%; padding:10px; border:1px solid var(--line); border-radius:8px; background:var(--panel); color:var(--text); font:inherit; }
  textarea { min-height:70px; resize:vertical; }
  .examples { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
  .examples button { border:1px solid var(--line); background:var(--panel); color:var(--text); border-radius:999px; padding:4px 10px; font-size:13px; cursor:pointer; }
  .send { margin-top:12px; padding:10px 18px; border:0; border-radius:8px; background:var(--accent); color:#fff; font:inherit; cursor:pointer; }
  .send:disabled { opacity:.5; cursor:wait; }
  .out { margin-top:20px; padding:14px; border:1px solid var(--line); border-radius:8px; background:var(--panel); white-space:pre-wrap; word-break:break-word; }
  .out.err { color:var(--err); }
  .out.md { white-space:normal; }
  .out.md > :first-child { margin-top:0; } .out.md > :last-child { margin-bottom:0; }
  .out.md h3, .out.md h4, .out.md h5, .out.md h6 { margin:14px 0 6px; font-size:15px; }
  .out.md p, .out.md ul, .out.md ol { margin:8px 0; } .out.md ul, .out.md ol { padding-left:22px; }
  .out.md code { padding:1px 4px; border-radius:4px; background:var(--bg); font-size:13px; }
  .out.md hr { border:0; border-top:1px solid var(--line); margin:12px 0; }
  .tbl { overflow-x:auto; margin:8px 0; }
  .tbl table { border-collapse:collapse; font-size:14px; }
  .tbl th, .tbl td { border:1px solid var(--line); padding:5px 10px; text-align:left; white-space:nowrap; }
  .tbl th { background:var(--bg); }
  details { margin-top:10px; }
  summary { cursor:pointer; color:var(--muted); font-size:13px; }
  pre { margin:6px 0 0; padding:10px; overflow-x:auto; background:var(--bg); border-radius:6px; font-size:12px; }
</style>
</head>
<body>
<main>
  <h1>AI 비용 분석 Agent</h1>
  <p class="sub">회사 토큰을 붙여 넣고 Bedrock 비용을 물어보세요. 토큰은 이 페이지에 저장되지 않습니다.</p>
  <label for="token">회사 토큰 (Bearer 뒤에 들어갈 값)</label>
  <input id="token" type="password" autocomplete="off" placeholder="토큰 붙여넣기">
  <label for="q">질문</label>
  <textarea id="q">이번 달 팀별 비용 알려줘</textarea>
  <div class="examples" id="examples"></div>
  <button class="send" id="send">물어보기</button>
  <div id="result"></div>
</main>
<script>
  // md:start 마크다운 변환기. 먼저 전부 이스케이프하고, 정해 둔 태그만 다시 만든다(LLM 답변에 HTML 이 끼어들 수 없다)
  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function inline(s) {
    return s.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }
  const LIST = /^(\s*)([-*]|\d+\.)\s+(.*)$/, HEADING = /^(#{1,4})\s+(.*)$/, RULE = /^\s*(-{3,}|\*{3,})\s*$/;
  const isRow = l => /^\s*\|.*\|\s*$/.test(l);
  const isSep = l => /^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{0,}:?\s*\|?\s*$/.test(l);
  const cells = l => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(c => inline(c.trim()));
  function renderMarkdown(md) {
    const lines = esc(md).split(/\r?\n/), out = [];
    let i = 0;
    while (i < lines.length) {
      const l = lines[i];
      if (isRow(l) && i + 1 < lines.length && isSep(lines[i + 1])) {
        const head = cells(l), body = [];
        for (i += 2; i < lines.length && isRow(lines[i]); i++) body.push(cells(lines[i]));
        out.push('<div class="tbl"><table><thead><tr>' + head.map(c => `<th>${c}</th>`).join("") + "</tr></thead><tbody>"
          + body.map(r => "<tr>" + r.map(c => `<td>${c}</td>`).join("") + "</tr>").join("") + "</tbody></table></div>");
        continue;
      }
      let m = l.match(HEADING);
      if (m) { const n = Math.min(m[1].length + 2, 6); out.push(`<h${n}>${inline(m[2])}</h${n}>`); i++; continue; }
      if (RULE.test(l)) { out.push("<hr>"); i++; continue; }
      if (LIST.test(l)) {
        const ordered = /^\s*\d+\./.test(l), start = ordered ? parseInt(l.trim(), 10) : 1, base = l.match(LIST)[1].length, items = [];
        while (i < lines.length) {
          if (!lines[i].trim()) {
            let j = i;
            while (j < lines.length && !lines[j].trim()) j++;
            if (j < lines.length && LIST.test(lines[j])) { i = j; continue; }
            break;
          }
          if (!LIST.test(lines[i]) && !/^\s{2,}\S/.test(lines[i])) break;
          const lm = lines[i].match(LIST);
          if (lm && (lm[1].length <= base || !items.length)) items.push({ html: inline(lm[3]), subs: [] });
          else if (lm) items[items.length - 1].subs.push(inline(lm[3]));
          else items[items.length - 1].html += "<br>" + inline(lines[i].trim());
          i++;
        }
        const tag = ordered ? "ol" : "ul", attr = ordered && start !== 1 ? ` start="${start}"` : "";
        out.push(`<${tag}${attr}>` + items.map(it => "<li>" + it.html
          + (it.subs.length ? "<ul>" + it.subs.map(x => `<li>${x}</li>`).join("") + "</ul>" : "") + "</li>").join("") + `</${tag}>`);
        continue;
      }
      if (!l.trim()) { i++; continue; }
      const para = [inline(l)];
      for (i++; i < lines.length && lines[i].trim() && !isRow(lines[i]) && !HEADING.test(lines[i])
           && !LIST.test(lines[i]) && !RULE.test(lines[i]); i++) para.push(inline(lines[i]));
      out.push("<p>" + para.join("<br>") + "</p>");
    }
    return out.join("");
  }
  // md:end
  const EXAMPLES = ["이번 달 팀별 비용 알려줘", "지난달 대비 이번 달 팀별 비용이 왜 늘었어?",
    "claude-sonnet를 claude-haiku로 바꾸면 9월 비용이 얼마나 줄어?", "9월 비용 중 태그 없는 미귀속 비용은 얼마야?",
    "9월 팀별·모델별 비용 표로 보여줘", "고객지원팀 모델별로 지난달 대비 뭐가 늘었어?",
    "팀 × 모델 조합별로 지난달보다 가장 많이 늘어난 건?"];
  const q = document.getElementById("q"), token = document.getElementById("token");
  const send = document.getElementById("send"), result = document.getElementById("result");
  for (const text of EXAMPLES) {
    const b = document.createElement("button");
    b.textContent = text;
    b.onclick = () => { q.value = text; };
    document.getElementById("examples").append(b);
  }
  function block(title, value) {
    const d = document.createElement("details"), s = document.createElement("summary"), pre = document.createElement("pre");
    s.textContent = title;
    pre.textContent = JSON.stringify(value, null, 2);
    d.append(s, pre);
    return d;
  }
  function show(text, isError, markdown) {
    result.replaceChildren();
    const div = document.createElement("div");
    div.className = "out" + (isError ? " err" : "") + (markdown ? " md" : "");
    if (markdown) div.innerHTML = renderMarkdown(text);
    else div.textContent = text;
    result.append(div);
    return div;
  }
  send.onclick = async () => {
    send.disabled = true;
    show("답변을 만드는 중입니다…");
    try {
      const headers = { "Content-Type": "application/json" };
      if (token.value.trim()) headers["Authorization"] = "Bearer " + token.value.trim();
      const r = await fetch("/query", { method: "POST", headers, body: JSON.stringify({ question: q.value }) });
      const body = await r.json().catch(() => ({}));
      if (r.status === 401) { show("401 인증 실패: 토큰이 없거나 올바르지 않습니다. 회사 토큰을 확인해 주세요.", true); return; }
      if (!r.ok) { show(`요청 실패(${r.status}): ` + JSON.stringify(body.detail ?? body), true); return; }
      const div = show(body.answer, false, true);
      div.after(block(`contexts (${body.contexts.length})`, body.contexts.map(c => {
        try { return { tool: c.tool, content: JSON.parse(c.content) }; } catch { return c; }
      })), block("trace", body.trace));
    } catch (e) {
      show("서버에 연결하지 못했습니다: " + e, true);
    } finally {
      send.disabled = false;
    }
  };
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui() -> str:
    """시연용 페이지. 토큰은 사용자가 붙여 넣고, 서버는 토큰 목록을 내주지 않는다."""
    return UI_HTML
