"""시연용 화면. 페이지 HTML·JS 문자열과 페이지 라우터만 두고, 인증과 데이터는 src/api.py 가 맡는다.

페이지: GET / (왼쪽 비용 대시보드 + 오른쪽 질문 패널). GET /dashboard 는 / 로 보낸다.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

APP_HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 비용 분석</title>
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
  main { position:relative; max-width:1480px; margin:0 auto; padding:24px 16px 48px; }
  .layout { display:grid; grid-template-columns:minmax(0, 1fr) 380px; gap:16px; align-items:start; }
  aside.ask { position:sticky; top:16px; max-height:calc(100vh - 32px); display:flex; flex-direction:column; gap:10px;
              padding:16px; border:1px solid var(--line); border-radius:10px; background:var(--panel); min-width:0; }
  @media (max-width: 960px) {
    .layout { grid-template-columns:minmax(0, 1fr); }
    aside.ask { position:static; max-height:none; }
    #history { max-height:none; }
  }
  .examples { display:flex; flex-wrap:wrap; gap:6px; }
  .examples button { border:1px solid var(--line); background:var(--bg); color:var(--text); border-radius:999px; padding:3px 10px; font:inherit; font-size:12px; cursor:pointer; text-align:left; }
  #history { flex:1 1 auto; overflow-y:auto; display:flex; flex-direction:column; gap:10px; min-height:80px; }
  details.ex { margin:0; } details.ex .examples { margin-top:6px; }
  .q { align-self:flex-end; max-width:90%; padding:8px 12px; border-radius:12px 12px 2px 12px; background:var(--bg); border:1px solid var(--line); font-size:14px; white-space:pre-wrap; word-break:break-word; }
  .out { padding:10px 12px; border:1px solid var(--line); border-radius:10px; font-size:14px; white-space:pre-wrap; word-break:break-word; }
  .out.err { color:var(--err); }
  .out.wait { color:var(--muted); }
  .out.md { white-space:normal; }
  .out.md > :first-child { margin-top:0; } .out.md > :last-child { margin-bottom:0; }
  .out.md h3, .out.md h4, .out.md h5, .out.md h6 { margin:12px 0 6px; font-size:14px; color:var(--text); }
  .out.md p, .out.md ul, .out.md ol { margin:6px 0; } .out.md ul, .out.md ol { padding-left:20px; }
  .out.md code { padding:1px 4px; border-radius:4px; background:var(--bg); font-size:12px; }
  .out.md hr { border:0; border-top:1px solid var(--line); margin:10px 0; }
  .out.md .tbl { margin:6px 0; }
  .out.md th, .out.md td { padding:4px 8px; border:1px solid var(--line); text-align:left; }
  .turn details { margin-top:4px; }
  .turn pre { margin:4px 0 0; padding:8px; max-height:280px; overflow:auto; background:var(--bg); border-radius:6px; font-size:11px; }
  .composer { display:flex; flex-direction:column; gap:6px; }
  .composer textarea { width:100%; min-height:64px; resize:vertical; padding:9px 10px; border:1px solid var(--line); border-radius:8px; background:var(--bg); color:var(--text); font:inherit; }
  .composer .row { display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:12px; color:var(--faint); }
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
    <h1>AI 비용 분석</h1>
  </header>
  <p class="sub">회사 토큰을 붙여 넣으면 그 회사의 Bedrock 비용만 보이고, 오른쪽에서 질문할 수 있습니다. 모든 숫자는 서버 도구가 계산한 값이고, 토큰은 이 페이지에 저장되지 않습니다.</p>
  <div class="controls">
    <label class="grow">회사 토큰 (Bearer 뒤에 들어갈 값)<input id="token" type="password" autocomplete="off" placeholder="토큰 붙여넣기"></label>
    <label>기준 달<select id="month"><option value="2026-09">2026-09</option><option value="2026-08">2026-08</option></select></label>
    <button class="go" id="load">불러오기</button>
  </div>
  <div class="layout">
    <div id="view"><div class="msg">토큰을 붙여 넣고 불러오기를 누르세요.</div></div>
    <aside class="ask" aria-label="질문하기">
      <h2 style="margin:0">질문하기</h2>
      <details class="ex" id="ex" open><summary>예시 질문</summary><div class="examples" id="examples"></div></details>
      <div id="history" aria-live="polite"><p class="hint">질문을 입력하거나 예시를 눌러 보세요. 이 페이지에서 물은 질문과 답이 여기에 쌓입니다(새로고침하면 사라짐).</p></div>
      <div class="composer">
        <textarea id="q" placeholder="예: 이번 달 팀별 비용 알려줘"></textarea>
        <div class="row"><span>Enter 보내기 · Shift+Enter 줄바꿈</span><button class="go" id="send">물어보기</button></div>
      </div>
    </aside>
  </div>
  <div class="tip" id="tip"></div>
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

  // 질문 패널: 이 페이지에서 물은 질문과 답을 쌓는다. 서버에는 지금처럼 질문 하나만 보낸다
  const q = $("q"), send = $("send"), history = $("history");
  for (const text of EXAMPLES) {
    const b = h("button", { type: "button" }, text);
    b.onclick = () => { q.value = text; q.focus(); };
    $("examples").append(b);
  }
  function block(title, value) {
    const pre = h("pre");
    pre.textContent = JSON.stringify(value, null, 2);
    return h("details", {}, h("summary", {}, title), pre);
  }
  function setAnswer(div, text, kind) {
    div.className = "out" + (kind ? " " + kind : "");
    if (kind === "md") div.innerHTML = renderMarkdown(text);
    else div.textContent = text;
  }
  async function ask(question) {
    if (!question.trim() || send.disabled) return;
    if (history.querySelector(".hint")) { history.replaceChildren(); $("ex").open = false; }
    const answer = h("div"), turn = h("div", { class: "turn" }, answer);
    history.append(h("div", { class: "q" }, question), turn);
    setAnswer(answer, "답변을 만드는 중입니다…", "wait");
    history.scrollTop = history.scrollHeight;
    send.disabled = true;
    try {
      const headers = { "Content-Type": "application/json" }, token = $("token").value.trim();
      if (token) headers["Authorization"] = "Bearer " + token;
      const r = await fetch("/query", { method: "POST", headers, body: JSON.stringify({ question }) });
      const body = await r.json().catch(() => ({}));
      if (r.status === 401) return setAnswer(answer, "401 인증 실패: 토큰이 없거나 올바르지 않습니다. 회사 토큰을 확인해 주세요.", "err");
      if (!r.ok) return setAnswer(answer, `요청 실패(${r.status}): ` + JSON.stringify(body.detail ?? body), "err");
      setAnswer(answer, body.answer, "md");
      turn.append(block(`contexts (${body.contexts.length})`, body.contexts.map(c => {
        try { return { tool: c.tool, content: JSON.parse(c.content) }; } catch { return c; }
      })), block("trace", body.trace));
    } catch (e) {
      setAnswer(answer, "서버에 연결하지 못했습니다: " + e, "err");
    } finally {
      send.disabled = false;
      history.scrollTop = history.scrollHeight;
    }
  }
  // 넓은 화면에서 패널 높이를 화면에 남은 높이로 맞춰 입력창이 늘 보이게 한다(좁은 화면은 CSS 가 아래로 쌓는다)
  const aside = document.querySelector("aside.ask");
  function fitAside() {
    if (matchMedia("(max-width: 960px)").matches) { aside.style.maxHeight = ""; return; }
    aside.style.maxHeight = Math.max(320, innerHeight - Math.max(16, aside.getBoundingClientRect().top) - 16) + "px";
  }
  addEventListener("scroll", fitAside, { passive: true });
  addEventListener("resize", fitAside);
  fitAside();
  send.onclick = () => { const text = q.value; q.value = ""; ask(text); };
  q.onkeydown = e => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send.onclick(); } };
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def app_page() -> str:
    """대시보드와 질문 패널을 합친 페이지. 숫자는 GET /dashboard/data 와 POST /query 가 주고 페이지는 계산하지 않는다.
    토큰은 사용자가 붙여 넣고, 서버는 토큰 목록을 내주지 않는다."""
    return APP_HTML


@router.get("/dashboard", include_in_schema=False)
def dashboard() -> RedirectResponse:
    """옛 대시보드 주소. 합친 페이지(/)로 보낸다."""
    return RedirectResponse("/")
