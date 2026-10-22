"""시연용 화면. 페이지 HTML·JS 문자열과 페이지 라우터만 두고, 인증과 데이터는 src/api.py 가 맡는다.

페이지: GET / (질문 시연), GET /dashboard (비용 대시보드)
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
  <p class="sub">회사 토큰을 붙여 넣고 Bedrock 비용을 물어보세요. 토큰은 이 페이지에 저장되지 않습니다. <a href="/dashboard">대시보드 보기</a></p>
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


DASHBOARD_HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 비용 대시보드</title>
<style>
  :root {
    color-scheme: light;
    --bg:#f7f7f5; --panel:#fcfcfb; --text:#1d1d1b; --muted:#52514e; --faint:#8a8984; --line:#e4e4df; --grid:#ececE8;
    --accent:#2f5fd0; --err:#b3261e;
    --series-1:#2a78d6; --series-2:#eb6834;
    --heat-0:#cde2fb; --heat-1:#9ec5f4; --heat-2:#6da7ec; --heat-3:#3987e5; --heat-4:#256abf;
    --heat-ink-light:#0b0b0b; --heat-ink-dark:#ffffff;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --bg:#161615; --panel:#1a1a19; --text:#f0efec; --muted:#c3c2b7; --faint:#8f8e88; --line:#33332f; --grid:#2a2a27;
      --accent:#8fb0ff; --err:#ff8a80;
      --series-1:#3987e5; --series-2:#d95926;
      --heat-0:#0d366b; --heat-1:#104281; --heat-2:#1c5cab; --heat-3:#2a78d6; --heat-4:#5598e7;
      --heat-ink-light:#f0efec; --heat-ink-dark:#0b0b0b;
    }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:15px/1.5 system-ui, "Malgun Gothic", sans-serif; }
  main { position:relative; max-width:1080px; margin:0 auto; padding:24px 16px 48px; }
  header { display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:8px; }
  h1 { font-size:20px; margin:0; }
  h2 { font-size:15px; margin:0 0 12px; }
  h3 { font-size:13px; margin:14px 0 6px; color:var(--muted); font-weight:600; }
  a { color:var(--accent); }
  p.sub { margin:4px 0 16px; color:var(--muted); font-size:13px; }
  .controls { display:flex; flex-wrap:wrap; gap:10px; align-items:end; margin-bottom:16px; }
  .panel .controls { align-items:center; margin-bottom:8px; }
  .controls label { display:flex; flex-direction:column; gap:4px; font-size:13px; color:var(--muted); }
  .controls .grow { flex:1 1 260px; }
  input, select { padding:9px 10px; border:1px solid var(--line); border-radius:8px; background:var(--panel); color:var(--text); font:inherit; }
  button.go { padding:9px 18px; border:0; border-radius:8px; background:var(--accent); color:#fff; font:inherit; cursor:pointer; }
  button.go:disabled { opacity:.5; cursor:wait; }
  .msg { padding:14px; border:1px solid var(--line); border-radius:8px; background:var(--panel); }
  .msg.err { color:var(--err); }
  .grid { display:grid; gap:16px; }
  .kpis { grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); }
  .bars { grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); }
  .panel { padding:16px; border:1px solid var(--line); border-radius:10px; background:var(--panel); min-width:0; }
  .kpi .label { font-size:13px; color:var(--muted); }
  .kpi .value { font-size:26px; font-weight:650; margin:4px 0 2px; font-variant-numeric:tabular-nums; }
  .kpi .note { font-size:13px; color:var(--muted); font-variant-numeric:tabular-nums; }
  .section { margin-top:16px; }
  .barrow { display:grid; grid-template-columns:minmax(80px, 30%) 1fr auto; gap:8px; align-items:center; padding:3px 0; font-size:13px; }
  .barrow .name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .barrow .num { color:var(--muted); font-variant-numeric:tabular-nums; text-align:right; }
  .barrow svg { display:block; width:100%; height:14px; overflow:visible; }
  .barrow.un .name { color:var(--muted); white-space:normal; }
  .tag { display:inline-block; margin-left:4px; padding:0 5px; border:1px solid var(--line); border-radius:4px; font-size:11px; color:var(--muted); }
  .tbl { overflow-x:auto; }
  table { border-collapse:collapse; font-size:13px; font-variant-numeric:tabular-nums; }
  th, td { padding:6px 10px; text-align:right; white-space:nowrap; border-bottom:1px solid var(--line); }
  th:first-child, td:first-child { text-align:left; }
  thead th { color:var(--muted); font-weight:600; }
  tr.sum td, td.sum { font-weight:650; }
  td.heat { border:2px solid var(--panel); border-radius:4px; }
  .scale { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin-top:10px; font-size:12px; color:var(--muted); }
  .scale span.sw { width:22px; height:10px; border-radius:2px; display:inline-block; }
  .mom { grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); }
  ol.top { margin:0; padding-left:20px; font-size:13px; }
  ol.top li { padding:3px 0; }
  ol.top .d { font-weight:650; font-variant-numeric:tabular-nums; }
  ol.top .s { color:var(--muted); font-variant-numeric:tabular-nums; }
  .legend { display:flex; flex-wrap:wrap; gap:14px; font-size:13px; color:var(--muted); margin-bottom:6px; }
  .legend i { display:inline-block; width:14px; height:2px; vertical-align:middle; margin-right:6px; }
  #chart svg { display:block; width:100%; }
  .axis { fill:var(--muted); font-size:11px; }
  .tip { position:absolute; pointer-events:none; padding:8px 10px; border:1px solid var(--line); border-radius:8px; background:var(--panel);
         color:var(--text); font-size:12px; line-height:1.5; box-shadow:0 2px 8px rgba(0,0,0,.12); white-space:nowrap; display:none; z-index:2; }
  .tip b { font-variant-numeric:tabular-nums; }
  details { margin-top:10px; }
  summary { cursor:pointer; color:var(--muted); font-size:13px; }
  .hint { font-size:12px; color:var(--faint); margin-top:6px; }
</style>
</head>
<body>
<main>
  <header>
    <h1>AI 비용 대시보드</h1>
    <a href="/">질문 페이지로</a>
  </header>
  <p class="sub">회사 토큰을 붙여 넣으면 그 회사의 Bedrock 비용만 보입니다. 모든 숫자는 서버 도구가 계산한 값이고, 토큰은 이 페이지에 저장되지 않습니다.</p>
  <div class="controls">
    <label class="grow">회사 토큰 (Bearer 뒤에 들어갈 값)<input id="token" type="password" autocomplete="off" placeholder="토큰 붙여넣기"></label>
    <label>기준 달<select id="month"><option value="2026-09">2026-09</option><option value="2026-08">2026-08</option></select></label>
    <button class="go" id="load">불러오기</button>
  </div>
  <div id="view"><div class="msg">토큰을 붙여 넣고 불러오기를 누르세요.</div></div>
  <div class="tip" id="tip"></div>
</main>
<script>
  // dash:start 표시용 함수. 숫자는 서버가 준 문자열을 그대로 쓰고 자릿수 구분 기호만 넣는다(계산하지 않는다)
  function groupDigits(intPart) { return intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function usd(s) {
    const neg = s.startsWith("-"), [i, f] = s.replace("-", "").split(".");
    return (neg ? "-" : "") + "$" + groupDigits(i) + (f !== undefined ? "." + f : "");
  }
  function signedUsd(s) { return s.startsWith("-") || /^0(\.0+)?$/.test(s) ? usd(s) : "+" + usd(s); }
  function krw(n) { return "약 " + groupDigits(String(Math.abs(n))) + "원"; }
  function signedKrw(n) { return (n < 0 ? "-" : n > 0 ? "+" : "") + krw(n); }
  function pct(s) { return s === "신규" ? "신규" : (s.startsWith("-") ? s : "+" + s) + "%"; }
  // 그리기 비율: 막대 길이·색 진하기·선 위치에만 쓰고 화면에 숫자로 보이지 않는다
  function ratio(value, max) { return max > 0 ? Math.max(0, Number(value)) / max : 0; }
  function heatStep(value, max) { return Math.min(4, Math.floor(ratio(value, max) * 5)); }
  // dash:end

  const $ = id => document.getElementById(id);
  const SVG = "http://www.w3.org/2000/svg";
  const DIM_LABEL = { team: "팀", service: "서비스", model: "모델", feature: "기능" };
  function h(tag, props = {}, ...children) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) k === "class" ? e.className = v : e.setAttribute(k, v);
    for (const c of children) e.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return e;
  }
  function s(tag, attrs = {}, text) {
    const e = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text !== undefined) e.textContent = text;
    return e;
  }
  const tip = $("tip");
  function showTip(evt, lines) {
    tip.replaceChildren(...lines.map(([label, value]) => h("div", {}, label, value === undefined ? "" : h("b", {}, " " + value))));
    tip.style.display = "block";
    const box = document.querySelector("main").getBoundingClientRect();
    let x = evt.clientX - box.left + 12, y = evt.clientY - box.top + 12;
    if (x + tip.offsetWidth > box.width) x = evt.clientX - box.left - tip.offsetWidth - 12;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  function hideTip() { tip.style.display = "none"; }

  function kpiTile(label, value, note) {
    return h("div", { class: "panel kpi" }, h("div", { class: "label" }, label), h("div", { class: "value" }, value), h("div", { class: "note" }, note));
  }
  function renderKpi(k) {
    const t = k.total, u = k.unattributed;
    return h("div", { class: "grid kpis" },
      kpiTile(`${k.month} 합계`, usd(t.this_usd), krw(t.this_krw)),
      kpiTile(`${k.previous_month} 합계`, usd(t.last_usd), krw(t.last_krw)),
      kpiTile("전월 대비", signedUsd(t.delta_usd), `${pct(t.pct_or_new)} · ${signedKrw(t.delta_krw)}`),
      kpiTile("미귀속 (태그 없음)", usd(u.usd), `전체의 ${u.share_pct}% · ${krw(u.krw)}`));
  }

  function barRow(name, money, max, isUn, dimLabel) {
    const svg = s("svg", { "aria-hidden": "true" });
    const w = (ratio(money.usd, max) * 100).toFixed(2) + "%";
    svg.append(s("rect", { x: 0, y: 1, width: w, height: 12, rx: 3, fill: isUn ? "var(--series-2)" : "var(--series-1)" }));
    const row = h("div", { class: "barrow" + (isUn ? " un" : "") },
      h("span", { class: "name", title: name }, name, ...(isUn ? [h("span", { class: "tag" }, "태그 없음")] : [])),
      svg, h("span", { class: "num" }, usd(money.usd)));
    row.onmousemove = e => showTip(e, [[`${dimLabel}: ${name}`], ["", usd(money.usd)], ["", krw(money.krw)]]);
    row.onmouseleave = hideTip;
    return row;
  }
  function renderBars(breakdown) {
    const wrap = h("div", { class: "grid bars section" });
    for (const dim of ["team", "service", "model"]) {
      const b = breakdown[dim], max = Math.max(...[...b.rows.map(r => r.usd), b.unattributed.usd].map(Number));
      const panel = h("div", { class: "panel" }, h("h2", {}, `${DIM_LABEL[dim]}별 비용 · ${b.period}`));
      for (const r of b.rows) panel.append(barRow(r[dim], r, max, false, DIM_LABEL[dim]));
      panel.append(barRow("미귀속", b.unattributed, max, true, DIM_LABEL[dim]));
      panel.append(h("div", { class: "hint" }, `합계 ${usd(b.total.usd)} (미귀속 포함)`));
      wrap.append(panel);
    }
    return wrap;
  }

  function renderCross(c) {
    const [a, b] = c.group_by, rowKeys = c.subtotals[a].map(x => x[a]), colKeys = c.subtotals[b].map(x => x[b]);
    const cell = new Map(c.rows.map(r => [r[a] + "\u0000" + r[b], r]));
    const max = Math.max(...c.rows.map(r => Number(r.usd)));
    const head = h("tr", {}, h("th", {}, `${DIM_LABEL[a]} / ${DIM_LABEL[b]}`), ...colKeys.map(k => h("th", {}, k)), h("th", {}, "소계"));
    const body = h("tbody");
    for (const rk of rowKeys) {
      const tr = h("tr", {}, h("td", {}, rk));
      for (const ck of colKeys) {
        const r = cell.get(rk + "\u0000" + ck);
        if (!r) { tr.append(h("td", {}, "–")); continue; }
        const step = heatStep(r.usd, max), td = h("td", { class: "heat" }, usd(r.usd));
        td.style.background = `var(--heat-${step})`;
        td.style.color = step >= 3 ? "var(--heat-ink-dark)" : "var(--heat-ink-light)";
        td.onmousemove = e => showTip(e, [[`${rk} × ${ck}`], ["", usd(r.usd)], ["", krw(r.krw)]]);
        td.onmouseleave = hideTip;
        tr.append(td);
      }
      tr.append(h("td", { class: "sum" }, usd(c.subtotals[a].find(x => x[a] === rk).usd)));
      body.append(tr);
    }
    body.append(h("tr", { class: "sum" }, h("td", {}, "소계"), ...colKeys.map(k => h("td", {}, usd(c.subtotals[b].find(x => x[b] === k).usd))),
      h("td", {}, usd(c.tagged_total.usd))));
    const un = new Map((c.unattributed.by_model || []).map(x => [x.model, x]));
    body.append(h("tr", {}, h("td", {}, "미귀속 (태그 없음)"), ...colKeys.map(k => h("td", {}, un.has(k) ? usd(un.get(k).usd) : "–")),
      h("td", { class: "sum" }, usd(c.unattributed.usd))));
    body.append(h("tr", { class: "sum" }, h("td", {}, "전체 합계"), ...colKeys.map(() => h("td", {}, "")), h("td", {}, usd(c.total.usd))));
    const swatches = [0, 1, 2, 3, 4].map(i => { const sw = h("span", { class: "sw" }); sw.style.background = `var(--heat-${i})`; return sw; });
    const scale = h("div", { class: "scale" }, "적음", ...swatches, "많음",
      h("span", {}, " · 칸 색은 태그된 칸끼리 비교한 크기입니다. 미귀속은 팀에 나누지 않고 모델별로만 따로 적었습니다"));
    return h("div", { class: "panel section" }, h("h2", {}, `${DIM_LABEL[a]} × ${DIM_LABEL[b]} 비용 · ${c.period}`),
      h("div", { class: "tbl" }, h("table", {}, h("thead", {}, head), body)), scale);
  }

  function momList(m, dim) {
    if (!m.items.length) return h("p", { class: "hint" }, "해당 항목이 없습니다.");
    return h("ol", { class: "top" }, ...m.items.map(i => h("li", {}, `${i[dim]} `, h("span", { class: "d" }, signedUsd(i.delta_usd)),
      h("span", { class: "s" }, ` (${pct(i.pct_or_new)}) · ${usd(i.last_usd)} → ${usd(i.this_usd)}`))));
  }
  function renderMom(mom, scopeValue, names) {
    const sel = h("select", { id: "scope" }, h("option", { value: "" }, "회사 전체"),
      ...names.team.map(t => h("option", { value: "team:" + t }, `팀: ${t}`)),
      ...names.service.map(v => h("option", { value: "service:" + v }, `서비스: ${v}`)));
    sel.value = scopeValue;
    sel.onchange = () => load();
    const any = Object.values(mom.increase)[0];
    const panel = h("div", { class: "panel section" },
      h("div", { class: "controls" }, h("h2", { style: "margin:0;flex:1" }, `전월 대비 상위 3 · ${any.last_month} → ${any.this_month}`), h("label", {}, "범위", sel)));
    const cols = h("div", { class: "grid mom" });
    for (const [direction, title] of [["increase", "가장 많이 늘어난 항목"], ["decrease", "가장 많이 줄어든 항목"]]) {
      const col = h("div", {}, h("h2", {}, title));
      for (const [dim, m] of Object.entries(mom[direction])) {
        col.append(h("h3", {}, `${DIM_LABEL[dim]}별`), momList(m, dim));
      }
      cols.append(col);
    }
    panel.append(cols);
    panel.append(h("p", { class: "hint" }, any.unattributed
      ? `미귀속(태그 없음)은 순위에서 뺐습니다: ${usd(any.unattributed.last_usd)} → ${usd(any.unattributed.this_usd)} (${signedUsd(any.unattributed.delta_usd)})`
      : "범위를 좁히면 미귀속은 빠집니다."));
    return panel;
  }

  function drawDaily(daily, box) {
    box.replaceChildren();
    const W = Math.max(300, box.clientWidth), H = 240, L = 12, R = 64, T = 24, B = 26;
    const days = daily.days, n = days.length;
    const peak = days.reduce((p, d) => Number(d.usd) > Number(p.usd) ? d : p, days[0]);
    const x = i => L + (W - L - R) * (n === 1 ? 0.5 : i / (n - 1));
    const y = v => T + (H - T - B) * (1 - ratio(v, Number(peak.usd)));
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": `${daily.period} 일별 비용 추이` });
    svg.append(s("line", { x1: L, x2: W - R, y1: y(0), y2: y(0), stroke: "var(--line)" }),
      s("line", { x1: L, x2: W - R, y1: y(peak.usd), y2: y(peak.usd), stroke: "var(--grid)" }),
      s("text", { x: L, y: y(peak.usd) - 8, class: "axis" }, `최고 ${usd(peak.usd)} (${peak.date.slice(5)})`));
    days.forEach((d, i) => { if (i % 7 === 0) svg.append(s("text", { x: x(i), y: H - 8, class: "axis", "text-anchor": i ? "middle" : "start" }, d.date.slice(5))); });
    const series = [["usd", "var(--series-1)", "전체"], ["unattributed_usd", "var(--series-2)", "미귀속"]];
    for (const [key, color, label] of series) {
      svg.append(s("path", { d: days.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`).join(""),
        fill: "none", stroke: color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
      svg.append(s("text", { x: x(n - 1) + 8, y: y(days[n - 1][key]) + 4, class: "axis" }, label));
    }
    const cross = s("line", { y1: T, y2: H - B, stroke: "var(--muted)", "stroke-width": 1, visibility: "hidden" });
    const dots = series.map(([, color]) => s("circle", { r: 4.5, fill: color, stroke: "var(--panel)", "stroke-width": 2, visibility: "hidden" }));
    const hit = s("rect", { x: 0, y: 0, width: W - R + 8, height: H, fill: "transparent" });
    svg.append(cross, ...dots, hit);
    hit.onmousemove = e => {
      const r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * (W / r.width);
      const i = Math.max(0, Math.min(n - 1, Math.round((px - L) / ((W - L - R) / Math.max(1, n - 1))))), d = days[i];
      cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("visibility", "visible");
      series.forEach(([key], j) => { dots[j].setAttribute("cx", x(i)); dots[j].setAttribute("cy", y(d[key])); dots[j].setAttribute("visibility", "visible"); });
      showTip(e, [[d.date], ["전체", `${usd(d.usd)} (${krw(d.krw)})`], ["미귀속", `${usd(d.unattributed_usd)} (${krw(d.unattributed_krw)})`]]);
    };
    hit.onmouseleave = () => { hideTip(); cross.setAttribute("visibility", "hidden"); dots.forEach(c => c.setAttribute("visibility", "hidden")); };
    box.append(svg);
  }
  function renderDaily(daily) {
    const box = h("div", { id: "chart" });
    const legend = h("div", { class: "legend" }, ...[["var(--series-1)", "전체"], ["var(--series-2)", "미귀속 (태그 없음)"]].map(([c, t]) => {
      const i = h("i"); i.style.background = c; return h("span", {}, i, t);
    }));
    const table = h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "날짜"), h("th", {}, "전체"), h("th", {}, "미귀속"))),
      h("tbody", {}, ...daily.days.map(d => h("tr", {}, h("td", {}, d.date), h("td", {}, usd(d.usd)), h("td", {}, usd(d.unattributed_usd))))));
    const panel = h("div", { class: "panel section" }, h("h2", {}, `일별 추이 · ${daily.period} (월 합계 ${usd(daily.total.usd)})`), legend, box,
      h("p", { class: "hint" }, "일별 금액은 날마다 반올림한 값이라 더하면 월 합계와 몇 센트 다를 수 있습니다."),
      h("details", {}, h("summary", {}, "표로 보기"), h("div", { class: "tbl" }, table)));
    requestAnimationFrame(() => drawDaily(daily, box));
    let t;
    window.onresize = () => { clearTimeout(t); t = setTimeout(() => drawDaily(daily, box), 150); };
    return panel;
  }

  function render(body, scopeValue) {
    const names = { team: body.breakdown.team.rows.map(r => r.team).sort(), service: body.breakdown.service.rows.map(r => r.service).sort() };
    $("view").replaceChildren(renderKpi(body.kpi), renderBars(body.breakdown), renderCross(body.cross),
      renderMom(body.mom, scopeValue, names), renderDaily(body.daily));
  }
  function message(text, isError) { hideTip(); $("view").replaceChildren(h("div", { class: "msg" + (isError ? " err" : "") }, text)); }
  async function load() {
    const scopeSel = $("scope"), scopeValue = scopeSel ? scopeSel.value : "";
    const params = new URLSearchParams({ month: $("month").value });
    if (scopeValue) { const at = scopeValue.indexOf(":"); params.set("scope_" + scopeValue.slice(0, at), scopeValue.slice(at + 1)); }
    const headers = {}, token = $("token").value.trim();
    if (token) headers["Authorization"] = "Bearer " + token;
    $("load").disabled = true;
    try {
      const r = await fetch("/dashboard/data?" + params, { headers });
      const body = await r.json().catch(() => ({}));
      if (r.status === 401) return message("401 인증 실패: 토큰이 없거나 올바르지 않습니다. 회사 토큰을 확인해 주세요.", true);
      if (!r.ok) return message(`요청 실패(${r.status}): ` + JSON.stringify(body.detail ?? body), true);
      render(body, scopeValue);
    } catch (e) {
      message("서버에 연결하지 못했습니다: " + e, true);
    } finally {
      $("load").disabled = false;
    }
  }
  $("load").onclick = () => load();
  $("month").onchange = () => { if ($("token").value.trim()) load(); };
</script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> str:
    """비용 대시보드 페이지. 숫자는 GET /dashboard/data 가 주고 페이지는 계산하지 않는다. 서버는 토큰 목록을 내주지 않는다."""
    return DASHBOARD_HTML
