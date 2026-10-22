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
<title>FinOps Radar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap">
<style>
  :root {
    color-scheme: light;
    --bg:#f3f5fa; --panel:#ffffff; --panel-2:#f6f8fc; --text:#101828; --muted:#475467; --faint:#8a94a6; --line:#e4e7ef; --grid:#eef0f5;
    --accent:#3b6ef5; --accent-2:#7c5cf0; --accent-soft:#eaf0ff; --err:#b3261e;
    --nav:#0b1530; --nav-2:#17275a; --nav-text:#eef2ff; --nav-muted:#9fabcf; --nav-field:rgba(255,255,255,.08); --nav-line:rgba(255,255,255,.14);
    --up:#c4320a; --up-bg:#fff1eb; --down:#0e7a43; --down-bg:#e7f6ee;
    --shadow:0 1px 2px rgba(16,24,40,.04), 0 8px 24px rgba(16,24,40,.06); --shadow-hover:0 2px 4px rgba(16,24,40,.06), 0 14px 32px rgba(16,24,40,.10);
    --series-1:#2a78d6; --series-2:#eb6834;
    --heat-0:#cde2fb; --heat-1:#9ec5f4; --heat-2:#6da7ec; --heat-3:#3987e5; --heat-4:#256abf;
    --heat-ink-light:#0b0b0b; --heat-ink-dark:#ffffff;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --bg:#0e1117; --panel:#161a22; --panel-2:#1c212b; --text:#eef1f7; --muted:#b4bccc; --faint:#7d879a; --line:#2a303c; --grid:#232935;
      --accent:#7aa2ff; --accent-2:#a58bff; --accent-soft:#1c2645; --err:#ff8a80;
      --nav:#060b1a; --nav-2:#0f1c40; --nav-text:#eef2ff; --nav-muted:#8f9bc0; --nav-field:rgba(255,255,255,.07); --nav-line:rgba(255,255,255,.12);
      --up:#ff9a76; --up-bg:#3a1d14; --down:#5fd39a; --down-bg:#12301f;
      --shadow:0 1px 2px rgba(0,0,0,.35), 0 8px 24px rgba(0,0,0,.25); --shadow-hover:0 2px 4px rgba(0,0,0,.4), 0 14px 32px rgba(0,0,0,.35);
      --series-1:#3987e5; --series-2:#d95926;
      --heat-0:#0d366b; --heat-1:#104281; --heat-2:#1c5cab; --heat-3:#2a78d6; --heat-4:#5598e7;
      --heat-ink-light:#f0efec; --heat-ink-dark:#0b0b0b;
    }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:15px/1.5 "Noto Sans KR", "Malgun Gothic", system-ui, sans-serif; -webkit-font-smoothing:antialiased; }
  a { color:var(--accent); }
  .sr { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }

  /* GNB */
  .gnb { position:sticky; top:0; z-index:5; color:var(--nav-text);
         background:linear-gradient(100deg, var(--nav) 0%, var(--nav-2) 100%); box-shadow:0 1px 0 var(--nav-line), 0 6px 20px rgba(6,11,26,.18); }
  .gnb-in { max-width:1480px; margin:0 auto; padding:10px 16px; display:flex; flex-wrap:wrap; align-items:center; gap:10px 16px; }
  .brand { display:flex; align-items:center; gap:10px; color:inherit; text-decoration:none; }
  .brand svg { flex:none; }
  .brand b { display:block; font-size:16px; letter-spacing:.2px; }
  .brand small { display:block; font-size:11.5px; color:var(--nav-muted); margin-top:-2px; }
  .tenant { display:inline-flex; align-items:center; gap:6px; padding:3px 10px 3px 8px; border-radius:999px; font-size:12.5px;
            background:rgba(122,162,255,.16); border:1px solid rgba(122,162,255,.35); color:#dbe5ff; }
  .tenant::before { content:""; width:7px; height:7px; border-radius:50%; background:#5fd39a; box-shadow:0 0 0 3px rgba(95,211,154,.18); }
  .tenant[hidden] { display:none; }
  .gnb-controls { margin-left:auto; display:flex; flex-wrap:wrap; align-items:center; gap:8px; flex:1 1 420px; justify-content:flex-end; }
  .field { display:flex; align-items:center; gap:8px; padding:0 10px; height:38px; border-radius:10px; background:var(--nav-field); border:1px solid var(--nav-line); }
  .field:focus-within { border-color:rgba(122,162,255,.7); box-shadow:0 0 0 3px rgba(122,162,255,.18); }
  .field.key { flex:1 1 220px; max-width:360px; }
  .field svg { flex:none; opacity:.75; }
  .field input, .field select { flex:1; min-width:0; height:36px; padding:0; border:0; outline:0; background:transparent; color:var(--nav-text); font:inherit; font-size:14px; }
  .field select option { color:#101828; }
  .field input::placeholder { color:var(--nav-muted); }
  button.go { height:38px; padding:0 18px; border:0; border-radius:10px; color:#fff; font:inherit; font-weight:600; cursor:pointer;
              background:linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%); box-shadow:0 4px 14px rgba(59,110,245,.35); }
  button.go:hover { filter:brightness(1.06); }
  button.go:disabled { opacity:.55; cursor:wait; }

  /* 본문 배치 */
  main { position:relative; max-width:1480px; margin:0 auto; padding:20px 16px 48px; }
  .layout { display:grid; grid-template-columns:minmax(0, 1fr) 390px; gap:20px; align-items:start; }
  @media (max-width: 960px) {
    .layout { grid-template-columns:minmax(0, 1fr); }
    aside.ask { position:static; max-height:none; }
    .gnb { position:static; }
  }
  .grid { display:grid; gap:16px; }
  .section { margin-top:20px; }
  .panel { padding:18px 20px; border:1px solid var(--line); border-radius:16px; background:var(--panel); box-shadow:var(--shadow); min-width:0;
           transition:box-shadow .2s ease, transform .2s ease; }
  .ph { display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 10px; margin-bottom:14px; }
  .ph h2 { font-size:15.5px; margin:0; letter-spacing:-.1px; }
  .ph .cap { font-size:12.5px; color:var(--faint); }
  .ph .grow { flex:1; }
  h2 { font-size:15px; margin:0 0 12px; }
  h3 { font-size:12.5px; margin:14px 0 6px; color:var(--muted); font-weight:600; letter-spacing:.2px; }
  select { padding:7px 10px; border:1px solid var(--line); border-radius:10px; background:var(--panel-2); color:var(--text); font:inherit; font-size:13px; }
  .msg { padding:16px; border:1px solid var(--line); border-radius:14px; background:var(--panel); box-shadow:var(--shadow); }
  .msg.err { color:var(--err); }

  /* 빈 화면 안내 */
  .empty { display:grid; grid-template-columns:minmax(0, 1fr) 260px; gap:24px; align-items:center; padding:32px; border-radius:20px;
           border:1px solid var(--line); box-shadow:var(--shadow);
           background:radial-gradient(120% 140% at 100% 0%, var(--accent-soft) 0%, var(--panel) 55%); }
  .empty h2 { font-size:22px; margin:0 0 6px; letter-spacing:-.3px; }
  .empty p { margin:0 0 18px; color:var(--muted); }
  .steps { list-style:none; margin:0; padding:0; display:grid; gap:10px; }
  .steps li { display:flex; gap:12px; align-items:flex-start; }
  .steps .n { flex:none; width:26px; height:26px; border-radius:50%; display:grid; place-items:center; font-size:13px; font-weight:700; color:#fff;
              background:linear-gradient(135deg, var(--accent), var(--accent-2)); }
  .steps b { display:block; font-size:14px; } .steps span { font-size:13px; color:var(--muted); }
  .empty .note { margin-top:18px; font-size:12px; color:var(--faint); }
  @media (max-width: 720px) { .empty { grid-template-columns:1fr; padding:22px; } .empty svg { display:none; } }

  /* KPI */
  .kpis { grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); }
  .kpi { position:relative; overflow:hidden; }
  .kpi::after { content:""; position:absolute; inset:0 0 auto 0; height:3px; background:linear-gradient(90deg, var(--accent), var(--accent-2)); opacity:.85; }
  .kpi .top { display:flex; align-items:center; gap:10px; }
  .kpi .ico { width:34px; height:34px; border-radius:10px; display:grid; place-items:center; background:var(--accent-soft); color:var(--accent); flex:none; }
  .kpi .label { font-size:13px; color:var(--muted); font-weight:500; }
  .kpi .value { font-size:28px; font-weight:700; margin:12px 0 4px; letter-spacing:-.6px; font-variant-numeric:tabular-nums; }
  .kpi .note { font-size:12.5px; color:var(--muted); font-variant-numeric:tabular-nums; display:flex; flex-wrap:wrap; align-items:center; gap:6px; }
  .delta { display:inline-flex; align-items:center; gap:3px; padding:1px 8px; border-radius:999px; font-size:12px; font-weight:650; }
  .delta.up { color:var(--up); background:var(--up-bg); } .delta.down { color:var(--down); background:var(--down-bg); } .delta.flat { color:var(--muted); background:var(--panel-2); }
  .meter { height:6px; border-radius:999px; background:var(--panel-2); border:1px solid var(--line); margin-top:10px; overflow:hidden; }
  .meter > i { display:block; height:100%; border-radius:999px; background:var(--series-2); }

  /* 막대 */
  .bars { grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); }
  .barrow { display:grid; grid-template-columns:minmax(80px, 32%) 1fr auto; gap:10px; align-items:center; padding:5px 6px; margin:0 -6px; border-radius:8px; font-size:13px; }
  .barrow:hover { background:var(--panel-2); }
  .barrow .name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .barrow .num { color:var(--muted); font-variant-numeric:tabular-nums; text-align:right; }
  .barrow svg { display:block; width:100%; height:14px; overflow:visible; }
  .barrow.un .name { color:var(--muted); white-space:normal; }
  .tag { display:inline-block; margin-left:4px; padding:0 6px; border-radius:999px; font-size:10.5px; color:var(--muted); background:var(--panel-2); border:1px solid var(--line); }
  .hint { font-size:12px; color:var(--faint); margin-top:8px; }

  /* 표 */
  .tbl { overflow-x:auto; }
  table { border-collapse:collapse; font-size:13px; font-variant-numeric:tabular-nums; }
  th, td { padding:7px 10px; text-align:right; white-space:nowrap; border-bottom:1px solid var(--line); }
  th:first-child, td:first-child { text-align:left; }
  thead th { color:var(--faint); font-weight:600; font-size:12px; text-transform:none; }
  tr.sum td, td.sum { font-weight:650; }
  td.heat { border:2px solid var(--panel); border-radius:6px; }
  .scale { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin-top:12px; font-size:12px; color:var(--muted); }
  .scale span.sw { width:22px; height:10px; border-radius:3px; display:inline-block; }

  /* 전월 대비 */
  .mom { grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:20px; }
  .mom .colh { display:flex; align-items:center; gap:8px; font-size:14px; font-weight:650; margin:0 0 4px; }
  ol.top { margin:0; padding:0; list-style:none; font-size:13px; counter-reset:r; }
  ol.top li { counter-increment:r; display:flex; flex-wrap:wrap; align-items:baseline; gap:2px 8px; padding:6px 8px; margin:0 -8px; border-radius:8px; }
  ol.top li:hover { background:var(--panel-2); }
  ol.top li::before { content:counter(r); font-size:11px; font-weight:700; color:var(--faint); width:14px; }
  ol.top .d { font-weight:650; font-variant-numeric:tabular-nums; }
  ol.top .s { color:var(--muted); font-variant-numeric:tabular-nums; }

  /* 일별 */
  .legend { display:flex; flex-wrap:wrap; gap:14px; font-size:13px; color:var(--muted); margin-bottom:6px; }
  .legend i { display:inline-block; width:14px; height:2px; vertical-align:middle; margin-right:6px; }
  #chart svg { display:block; width:100%; }
  .axis { fill:var(--muted); font-size:11px; }
  .tip { position:absolute; pointer-events:none; padding:8px 10px; border:1px solid var(--line); border-radius:10px; background:var(--panel);
         color:var(--text); font-size:12px; line-height:1.5; box-shadow:var(--shadow-hover); white-space:nowrap; display:none; z-index:6; }
  .tip b { font-variant-numeric:tabular-nums; }
  details { margin-top:10px; }
  summary { cursor:pointer; color:var(--muted); font-size:13px; }

  /* 질문 패널 */
  aside.ask { position:sticky; top:84px; max-height:calc(100vh - 100px); display:flex; flex-direction:column; min-width:0;
              border:1px solid var(--line); border-radius:18px; background:var(--panel); box-shadow:var(--shadow); overflow:hidden; }
  .ask-h { display:flex; align-items:center; gap:10px; padding:14px 16px; border-bottom:1px solid var(--line);
           background:linear-gradient(180deg, var(--panel-2), var(--panel)); }
  .ask-h b { display:block; font-size:14.5px; } .ask-h small { display:block; font-size:12px; color:var(--faint); }
  .avatar { flex:none; width:32px; height:32px; border-radius:10px; display:grid; place-items:center; color:#fff;
            background:linear-gradient(135deg, var(--accent), var(--accent-2)); box-shadow:0 3px 10px rgba(59,110,245,.3); }
  .avatar.sm { width:26px; height:26px; border-radius:8px; box-shadow:none; }
  details.ex { margin:0; padding:10px 16px 0; } details.ex summary { font-size:12.5px; }
  .examples { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
  .examples button { border:1px solid var(--line); background:var(--panel-2); color:var(--text); border-radius:999px; padding:4px 11px; font:inherit; font-size:12px; cursor:pointer; text-align:left; }
  .examples button:hover { border-color:var(--accent); color:var(--accent); background:var(--accent-soft); }
  #history { flex:1 1 auto; overflow-y:auto; display:flex; flex-direction:column; gap:12px; min-height:90px; padding:14px 16px; }
  #history > .hint { margin:auto 0; text-align:center; }
  .q { align-self:flex-end; max-width:86%; padding:9px 13px; border-radius:16px 16px 4px 16px; color:#fff; font-size:14px; white-space:pre-wrap; word-break:break-word;
       background:linear-gradient(135deg, var(--accent), var(--accent-2)); box-shadow:0 3px 10px rgba(59,110,245,.22); }
  .turn { display:grid; grid-template-columns:26px minmax(0, 1fr); gap:8px; align-items:start; }
  .turn .body { min-width:0; }
  .out { padding:10px 13px; border:1px solid var(--line); border-radius:4px 16px 16px 16px; background:var(--panel-2); font-size:14px; white-space:pre-wrap; word-break:break-word; }
  .out.err { color:var(--err); }
  .out.md { white-space:normal; }
  .out.md > :first-child { margin-top:0; } .out.md > :last-child { margin-bottom:0; }
  .out.md h3, .out.md h4, .out.md h5, .out.md h6 { margin:12px 0 6px; font-size:14px; color:var(--text); }
  .out.md p, .out.md ul, .out.md ol { margin:6px 0; } .out.md ul, .out.md ol { padding-left:20px; }
  .out.md code { padding:1px 5px; border-radius:5px; background:var(--panel); font-size:12px; }
  .out.md hr { border:0; border-top:1px solid var(--line); margin:10px 0; }
  .out.md .tbl { margin:6px 0; }
  .out.md table { background:var(--panel); border-radius:8px; }
  .out.md th, .out.md td { padding:4px 8px; border:1px solid var(--line); text-align:left; }
  .dots { display:inline-flex; gap:4px; padding:4px 2px; }
  .dots i { width:7px; height:7px; border-radius:50%; background:var(--faint); animation:blink 1.2s infinite ease-in-out; }
  .dots i:nth-child(2) { animation-delay:.15s; } .dots i:nth-child(3) { animation-delay:.3s; }
  @keyframes blink { 0%, 80%, 100% { opacity:.25; transform:translateY(0); } 40% { opacity:1; transform:translateY(-3px); } }
  @media (prefers-reduced-motion: reduce) { .dots i { animation:none; opacity:.6; } .panel { transition:none; } }
  .turn details { margin-top:6px; } .turn summary { font-size:12px; }
  .turn pre { margin:4px 0 0; padding:8px; max-height:280px; overflow:auto; background:var(--panel-2); border:1px solid var(--line); border-radius:8px; font-size:11px; }
  .composer { padding:12px 16px 14px; border-top:1px solid var(--line); }
  .composer .box { display:flex; align-items:flex-end; gap:8px; padding:6px 6px 6px 12px; border:1px solid var(--line); border-radius:16px; background:var(--panel-2); }
  .composer .box:focus-within { border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-soft); }
  .composer textarea { flex:1; min-height:40px; max-height:160px; resize:none; padding:8px 0; border:0; outline:0; background:transparent; color:var(--text); font:inherit; font-size:14px; }
  .composer button.send { width:38px; height:38px; flex:none; display:grid; place-items:center; border:0; border-radius:12px; color:#fff; cursor:pointer;
                          background:linear-gradient(135deg, var(--accent), var(--accent-2)); }
  .composer button.send:disabled { opacity:.5; cursor:wait; }
  .composer .row { margin-top:6px; font-size:11.5px; color:var(--faint); }
</style>
</head>
<body>
<nav class="gnb">
  <div class="gnb-in">
    <a class="brand" href="/" aria-label="FinOps Radar 처음으로">
      <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">
        <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5b8cff"/><stop offset="1" stop-color="#9b7bff"/></linearGradient></defs>
        <rect width="34" height="34" rx="10" fill="url(#lg)"/>
        <circle cx="17" cy="17" r="10" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="1.6"/>
        <circle cx="17" cy="17" r="5.5" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="1.6"/>
        <path d="M17 17 L17 7 A10 10 0 0 1 26.5 13.9 Z" fill="#fff" fill-opacity=".35"/>
        <line x1="17" y1="17" x2="26.5" y2="13.9" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
        <circle cx="21.6" cy="10.8" r="1.8" fill="#fff"/>
      </svg>
      <span><b>FinOps Radar</b><small>Bedrock 비용 분석</small></span>
    </a>
    <span class="tenant" id="tenant" hidden></span>
    <div class="gnb-controls">
      <label class="field key">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="8" cy="15" r="4"/><path d="M10.8 12.2 20 3M16 7l3 3M14 9l2 2"/></svg>
        <span class="sr">회사 토큰 (Bearer 뒤에 들어갈 값)</span>
        <input id="token" type="password" autocomplete="off" placeholder="회사 토큰 붙여넣기">
      </label>
      <label class="field">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>
        <span class="sr">기준 달</span>
        <select id="month"><option value="2026-09">2026-09</option><option value="2026-08">2026-08</option></select>
      </label>
      <button class="go" id="load">불러오기</button>
    </div>
  </div>
</nav>
<main>
  <div class="layout">
    <div id="view"></div>
    <aside class="ask" aria-label="질문하기">
      <div class="ask-h">
        <span class="avatar"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.8 4.6L18.5 9l-4.7 1.4L12 15l-1.8-4.6L5.5 9l4.7-1.4z"/><path d="M19 15l.8 2 2 .8-2 .7-.8 2-.7-2-2-.7 2-.8z"/></svg></span>
        <span><b>비용 분석 에이전트</b><small>숫자는 도구가 계산한 값만 옮깁니다</small></span>
      </div>
      <details class="ex" id="ex" open><summary>예시 질문</summary><div class="examples" id="examples"></div></details>
      <div id="history" aria-live="polite"><p class="hint">질문을 입력하거나 예시를 눌러 보세요.<br>이 페이지에서 물은 질문과 답이 여기에 쌓입니다(새로고침하면 사라짐).</p></div>
      <div class="composer">
        <div class="box">
          <textarea id="q" rows="1" placeholder="무엇이든 물어보세요. 예: 이번 달 팀별 비용"></textarea>
          <button class="send" id="send" aria-label="물어보기" title="물어보기"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button>
        </div>
        <div class="row">Enter 보내기 · Shift+Enter 줄바꿈</div>
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

  // 아이콘은 선 그림(path d 목록)만 쓴다
  const ICONS = {
    wallet: ["M3 7a2 2 0 0 1 2-2h12v4", "M3 7v10a2 2 0 0 0 2 2h14V9H5a2 2 0 0 1-2-2z", "M16 14h.01"],
    calendar: ["M4 6h16v14H4z", "M4 10h16", "M9 3v4", "M15 3v4"],
    trend: ["M3 17l6-6 4 4 8-8", "M15 7h6v6"],
    tag: ["M3 12V4h8l10 10-8 8z", "M7.5 7.5h.01"],
    up: ["M12 19V5", "M5 12l7-7 7 7"],
    down: ["M12 5v14", "M5 12l7 7 7-7"],
  };
  function icon(name, size = 18) {
    const svg = s("svg", { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
      "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" });
    for (const d of ICONS[name]) svg.append(s("path", { d }));
    return svg;
  }
  function title(text, cap, ...extra) {
    return h("div", { class: "ph" }, h("h2", {}, text), ...(cap ? [h("span", { class: "cap" }, cap)] : []), ...extra);
  }
  // 증감 배지: 비용이 늘면 up, 줄면 down. 색만이 아니라 화살표와 부호 글자로도 구분한다
  function deltaBadge(deltaUsd, pctText) {
    const dir = deltaUsd.startsWith("-") ? "down" : /^0(\.0+)?$/.test(deltaUsd) ? "flat" : "up";
    return h("span", { class: "delta " + dir }, ...(dir === "flat" ? [] : [icon(dir, 12)]), pct(pctText));
  }
  function kpiTile(iconName, label, value, ...note) {
    return h("div", { class: "panel kpi" }, h("div", { class: "top" }, h("span", { class: "ico" }, icon(iconName)), h("span", { class: "label" }, label)),
      h("div", { class: "value" }, value), h("div", { class: "note" }, ...note));
  }
  function renderKpi(k) {
    const t = k.total, u = k.unattributed;
    const meter = h("div", { class: "meter", title: `전체의 ${u.share_pct}%` }, h("i"));
    meter.firstChild.style.width = Math.min(100, Number(u.share_pct)) + "%";
    const unTile = kpiTile("tag", "미귀속 (태그 없음)", usd(u.usd), `전체의 ${u.share_pct}% · ${krw(u.krw)}`);
    unTile.append(meter);
    return h("div", { class: "grid kpis" },
      kpiTile("wallet", `${k.month} 합계`, usd(t.this_usd), krw(t.this_krw)),
      kpiTile("calendar", `${k.previous_month} 합계`, usd(t.last_usd), krw(t.last_krw)),
      kpiTile("trend", "전월 대비", signedUsd(t.delta_usd), deltaBadge(t.delta_usd, t.pct_or_new), signedKrw(t.delta_krw)),
      unTile);
  }
  function emptyState() {
    const art = s("svg", { width: 240, height: 170, viewBox: "0 0 240 170", "aria-hidden": "true" });
    art.append(s("rect", { x: 10, y: 20, width: 220, height: 130, rx: 16, fill: "var(--panel)", stroke: "var(--line)" }));
    [[34, 90, 40], [66, 70, 60], [98, 50, 80], [130, 78, 52]].forEach(([x, y, hgt], i) =>
      art.append(s("rect", { x, y, width: 20, height: hgt, rx: 5, fill: i === 2 ? "var(--series-2)" : "var(--series-1)", opacity: i === 2 ? 1 : .85 })));
    art.append(s("path", { d: "M166 112 L184 84 L198 96 L216 58", fill: "none", stroke: "var(--accent-2)", "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round" }));
    art.append(s("circle", { cx: 216, cy: 58, r: 5, fill: "var(--accent-2)" }));
    const step = (n, b, t) => h("li", {}, h("span", { class: "n" }, n), h("div", {}, h("b", {}, b), h("span", {}, t)));
    return h("div", { class: "empty" },
      h("div", {}, h("h2", {}, "우리 회사 AI 비용을 한눈에"),
        h("p", {}, "팀·서비스·모델별 Bedrock 비용, 전월 대비 변화, 태그 없는 미귀속 비용을 보고 바로 질문할 수 있습니다."),
        h("ol", { class: "steps" },
          step(1, "회사 토큰 붙여넣기", "위쪽 열쇠 칸에 회사 토큰을 넣습니다."),
          step(2, "기준 달 고르고 불러오기", "2026-09 또는 2026-08 을 고릅니다."),
          step(3, "오른쪽에서 질문하기", "예시 질문을 누르거나 직접 물어봅니다.")),
        h("p", { class: "note" }, "모든 숫자는 서버 도구가 계산한 값이고, 토큰은 이 페이지에 저장되지 않습니다.")),
      art);
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
      const panel = h("div", { class: "panel" }, title(`${DIM_LABEL[dim]}별 비용`, `${b.period} · 미귀속은 따로`));
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
    return h("div", { class: "panel section" }, title(`${DIM_LABEL[a]} × ${DIM_LABEL[b]} 비용`, `${c.period} · 칸 색이 진할수록 큰 금액`),
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
      title("전월 대비 상위 3", `${any.last_month} → ${any.this_month} · USD 증감액 순`, h("span", { class: "grow" }), h("label", { class: "cap" }, "범위 ", sel)));
    const cols = h("div", { class: "grid mom" });
    for (const [direction, title] of [["increase", "가장 많이 늘어난 항목"], ["decrease", "가장 많이 줄어든 항목"]]) {
      const col = h("div", {}, h("div", { class: "colh" }, h("span", { class: "delta " + (direction === "increase" ? "up" : "down") }, icon(direction === "increase" ? "up" : "down", 12)), title));
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
    const panel = h("div", { class: "panel section" }, title("일별 추이", `${daily.period} · 월 합계 ${usd(daily.total.usd)}`), legend, box,
      h("p", { class: "hint" }, "일별 금액은 날마다 반올림한 값이라 더하면 월 합계와 몇 센트 다를 수 있습니다."),
      h("details", {}, h("summary", {}, "표로 보기"), h("div", { class: "tbl" }, table)));
    requestAnimationFrame(() => drawDaily(daily, box));
    let t;
    window.onresize = () => { clearTimeout(t); t = setTimeout(() => drawDaily(daily, box), 150); };
    return panel;
  }

  function render(body, scopeValue) {
    const names = { team: body.breakdown.team.rows.map(r => r.team).sort(), service: body.breakdown.service.rows.map(r => r.service).sort() };
    $("tenant").textContent = body.tenant.name;
    $("tenant").hidden = false;
    $("view").replaceChildren(renderKpi(body.kpi), renderBars(body.breakdown), renderCross(body.cross),
      renderMom(body.mom, scopeValue, names), renderDaily(body.daily));
  }
  function message(text, isError) {
    hideTip();
    $("tenant").hidden = true;
    $("view").replaceChildren(h("div", { class: "msg" + (isError ? " err" : "") }, text));
  }
  $("view").replaceChildren(emptyState());
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
    else if (kind === "wait") div.replaceChildren(h("span", { class: "dots", role: "status", "aria-label": text }, h("i"), h("i"), h("i")));
    else div.textContent = text;
  }
  function agentAvatar() {
    const a = h("span", { class: "avatar sm" });
    a.append(s("svg", { width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": 2.2, "stroke-linejoin": "round", "aria-hidden": "true" }));
    a.firstChild.append(s("path", { d: "M12 3l1.8 4.6L18.5 9l-4.7 1.4L12 15l-1.8-4.6L5.5 9l4.7-1.4z" }));
    return a;
  }
  async function ask(question) {
    if (!question.trim() || send.disabled) return;
    if (history.querySelector(".hint")) { history.replaceChildren(); $("ex").open = false; }
    const answer = h("div"), bubble = h("div", { class: "body" }, answer), turn = h("div", { class: "turn" }, agentAvatar(), bubble);
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
      bubble.append(block(`contexts (${body.contexts.length})`, body.contexts.map(c => {
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
    const stickTop = document.querySelector(".gnb").offsetHeight + 16;
    aside.style.top = stickTop + "px";
    aside.style.maxHeight = Math.max(320, innerHeight - Math.max(stickTop, aside.getBoundingClientRect().top) - 16) + "px";
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
