import base64

with open('C:/Users/Nimaa/OneDrive/Desktop/FIFA-WC-2026/.superpowers/brainstorm/1309-1778428415/content/trophy_nobg.png','rb') as f:
    b64 = base64.b64encode(f.read()).decode()
src = f"data:image/png;base64,{b64}"

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>FIFA WC 2026 – Design Preview</title>
<style>
  /* ── FIFA.com design tokens ── */
  :root {
    --bg:        #090b14;
    --surface:   #0e1020;
    --surface2:  #151829;
    --border:    #1e2340;
    --fifa-blue: #1a3fff;
    --blue-dark: #0d1d8a;
    --gold:      #f5c842;
    --gold-dim:  #c9a227;
    --text:      #ffffff;
    --text-sub:  #8b93b8;
    --text-dim:  #4a5280;
    --green:     #00d48a;
    --red:       #ff3b5c;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; min-height: 100vh; }

  /* ── HEADER ── */
  .site-header {
    background: linear-gradient(180deg, #05060f 0%, #090b14 100%);
    border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 50;
  }
  .top-bar {
    max-width: 1100px; margin: 0 auto;
    padding: 0 24px;
    display: flex; align-items: center; gap: 12px;
    height: 48px;
    border-bottom: 1px solid var(--border);
  }
  .fifa-wordmark {
    font-size: 13px; font-weight: 900; letter-spacing: 3px;
    color: var(--fifa-blue); text-transform: uppercase;
  }
  .wc-badge {
    font-size: 10px; font-weight: 700; color: var(--gold);
    background: rgba(245,200,66,0.12); border: 1px solid rgba(245,200,66,0.25);
    border-radius: 4px; padding: 2px 8px; letter-spacing: 1px;
  }

  /* ── HERO ── */
  .hero {
    position: relative; overflow: hidden;
    background: radial-gradient(ellipse at 50% -10%, #0d1d8a 0%, #090b14 55%);
    min-height: 340px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 48px 24px 36px;
    text-align: center;
  }
  .hero::before {
    content: '';
    position: absolute; inset: 0;
    background:
      radial-gradient(ellipse at 20% 80%, rgba(0,212,138,0.07) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 80%, rgba(26,63,255,0.1) 0%, transparent 50%);
  }
  /* diagonal stripe overlay like FIFA.com */
  .hero::after {
    content: '';
    position: absolute; inset: 0;
    background: repeating-linear-gradient(
      -45deg,
      rgba(255,255,255,0.012) 0px,
      rgba(255,255,255,0.012) 1px,
      transparent 1px,
      transparent 28px
    );
  }
  .hero-inner { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .trophy-img {
    height: 200px; object-fit: contain;
    filter: drop-shadow(0 0 40px rgba(245,200,66,0.8)) drop-shadow(0 0 80px rgba(26,63,255,0.4));
    animation: float 4s ease-in-out infinite;
  }
  .hero-eyebrow {
    font-size: 11px; font-weight: 700; letter-spacing: 3px;
    color: var(--fifa-blue); text-transform: uppercase;
  }
  .hero-title {
    font-size: 28px; font-weight: 900; line-height: 1.1;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #fff 30%, var(--gold) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .hero-sub { font-size: 13px; color: var(--text-sub); max-width: 380px; }
  .hero-cta {
    display: inline-flex; align-items: center; gap-8px;
    background: var(--fifa-blue); color: #fff;
    font-size: 13px; font-weight: 700; letter-spacing: 0.5px;
    padding: 12px 28px; border-radius: 6px;
    border: none; cursor: pointer;
    box-shadow: 0 0 24px rgba(26,63,255,0.5);
    margin-top: 4px;
  }

  /* ── NAV TABS ── */
  .nav-tabs {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex; max-width: 100%; overflow-x: auto;
  }
  .nav-tabs-inner {
    max-width: 1100px; margin: 0 auto; padding: 0 24px;
    display: flex; gap: 0;
  }
  .tab {
    padding: 14px 20px; font-size: 13px; font-weight: 600;
    color: var(--text-dim); border-bottom: 3px solid transparent;
    white-space: nowrap; cursor: pointer; transition: color 0.2s;
  }
  .tab.active { color: #fff; border-bottom-color: var(--fifa-blue); }
  .tab:hover:not(.active) { color: var(--text-sub); }

  /* ── MAIN CONTENT ── */
  .main { max-width: 1100px; margin: 0 auto; padding: 32px 24px; display: flex; flex-direction: column; gap: 28px; }

  /* ── SECTION HEADING ── */
  .section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
  .section-title { font-size: 16px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase; }
  .section-link  { font-size: 12px; color: var(--fifa-blue); font-weight: 600; cursor: pointer; }

  /* ── PREDICT CARD ── */
  .predict-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
  }
  .team-row {
    display: grid; grid-template-columns: 1fr auto 1fr; gap: 16px;
    align-items: end; margin-bottom: 20px;
  }
  .team-input-label { font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--text-sub); margin-bottom: 8px; }
  .team-input {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; padding: 12px 16px;
    color: var(--text-sub); font-size: 13px;
    display: flex; align-items: center; gap: 8px;
  }
  .team-input-placeholder { color: var(--text-dim); }
  .swap-btn {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; width: 42px; height: 42px;
    display: flex; align-items: center; justify-content: center;
    color: var(--text-sub); font-size: 16px; cursor: pointer;
  }
  .predict-btn {
    width: 100%; background: var(--fifa-blue);
    color: #fff; font-size: 14px; font-weight: 700; letter-spacing: 0.5px;
    padding: 14px; border-radius: 8px; border: none; cursor: pointer;
    box-shadow: 0 4px 20px rgba(26,63,255,0.4);
  }

  /* ── MATCH CARDS ── */
  .match-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .match-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 16px;
    display: flex; flex-direction: column; gap: 10px;
    cursor: pointer; transition: border-color 0.2s, transform 0.15s;
  }
  .match-card:hover { border-color: var(--fifa-blue); transform: translateY(-2px); }
  .match-meta { display: flex; justify-content: space-between; align-items: center; }
  .match-group { font-size: 10px; font-weight: 700; color: var(--fifa-blue); letter-spacing: 1px; text-transform: uppercase; }
  .match-date  { font-size: 10px; color: var(--text-dim); }
  .match-teams { display: flex; align-items: center; justify-content: space-between; }
  .match-team  { font-size: 13px; font-weight: 700; color: var(--text); }
  .match-vs    { font-size: 11px; color: var(--text-dim); }
  .prob-bar    { height: 3px; border-radius: 2px; background: var(--border); overflow: hidden; }
  .prob-fill   { height: 100%; border-radius: 2px; background: linear-gradient(90deg, var(--fifa-blue), #5b8fff); }

  /* ── RESULT CARD ── */
  .result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px; padding: 24px;
  }
  .result-score {
    display: flex; align-items: center; justify-content: center; gap: 24px;
    margin: 16px 0;
  }
  .result-team-name { font-size: 18px; font-weight: 800; }
  .result-score-num {
    font-size: 48px; font-weight: 900; line-height: 1;
    background: linear-gradient(135deg, #fff, var(--gold));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .result-dash { font-size: 32px; color: var(--text-dim); font-weight: 300; }
  .prob-row { display: flex; gap: 8px; margin-top: 12px; }
  .prob-pill {
    flex: 1; background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px; text-align: center;
  }
  .prob-pill-label { font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
  .prob-pill-val   { font-size: 18px; font-weight: 800; color: var(--text); }
  .prob-pill.win   { border-color: var(--fifa-blue); background: rgba(26,63,255,0.08); }
  .prob-pill.win .prob-pill-val { color: #5b8fff; }

  @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-18px)} }
</style>
</head>
<body>

<!-- HEADER -->
<header class="site-header">
  <div class="top-bar">
    <span class="fifa-wordmark">FIFA</span>
    <span class="wc-badge">WC 2026™</span>
    <span style="flex:1"></span>
    <span style="font-size:11px;color:#4a5280;">Predictor · Powered by AI</span>
  </div>
</header>

<!-- HERO -->
<div class="hero">
  <div class="hero-inner">
    <div class="hero-eyebrow">FIFA World Cup 2026™</div>
    <img class="trophy-img" src="TROPHY_SRC" alt="FIFA World Cup Trophy"/>
    <h1 class="hero-title">FIFA WC 2026 Predictor</h1>
    <p class="hero-sub">AI-powered match outcome predictions for the biggest tournament on Earth</p>
    <button class="hero-cta">Predict a Match</button>
  </div>
</div>

<!-- TABS -->
<div class="nav-tabs">
  <div class="nav-tabs-inner">
    <div class="tab active">Group Stage</div>
    <div class="tab">Predict Match</div>
  </div>
</div>

<!-- MAIN -->
<div class="main">

  <!-- Predict section -->
  <div>
    <div class="section-head">
      <span class="section-title">Select a Match</span>
      <span class="section-link">WC 2026 teams only ›</span>
    </div>
    <div class="predict-card">
      <div class="team-row">
        <div>
          <div class="team-input-label">Home Team</div>
          <div class="team-input"><span class="team-input-placeholder">Search home team…</span></div>
        </div>
        <div class="swap-btn">⇄</div>
        <div>
          <div class="team-input-label">Away Team</div>
          <div class="team-input"><span class="team-input-placeholder">Search away team…</span></div>
        </div>
      </div>
      <button class="predict-btn">Predict Outcome</button>
    </div>
  </div>

  <!-- Group matches -->
  <div>
    <div class="section-head">
      <span class="section-title">Group Stage</span>
      <span class="section-link">View all groups ›</span>
    </div>
    <div class="match-grid">
      <div class="match-card">
        <div class="match-meta"><span class="match-group">Group A</span><span class="match-date">Jun 11</span></div>
        <div class="match-teams"><span class="match-team">USA</span><span class="match-vs">vs</span><span class="match-team">Mexico</span></div>
        <div class="prob-bar"><div class="prob-fill" style="width:58%"></div></div>
      </div>
      <div class="match-card">
        <div class="match-meta"><span class="match-group">Group B</span><span class="match-date">Jun 12</span></div>
        <div class="match-teams"><span class="match-team">Brazil</span><span class="match-vs">vs</span><span class="match-team">Argentina</span></div>
        <div class="prob-bar"><div class="prob-fill" style="width:47%"></div></div>
      </div>
      <div class="match-card">
        <div class="match-meta"><span class="match-group">Group C</span><span class="match-date">Jun 12</span></div>
        <div class="match-teams"><span class="match-team">France</span><span class="match-vs">vs</span><span class="match-team">Germany</span></div>
        <div class="prob-bar"><div class="prob-fill" style="width:52%"></div></div>
      </div>
    </div>
  </div>

  <!-- Sample result -->
  <div>
    <div class="section-head">
      <span class="section-title">Prediction Result</span>
    </div>
    <div class="result-card">
      <div style="text-align:center;font-size:11px;color:#4a5280;margin-bottom:4px;">Group A · Jun 11, 2026 · FIFA World Cup 2026</div>
      <div class="result-score">
        <div style="text-align:center">
          <div class="result-team-name">USA</div>
          <div style="font-size:11px;color:#4a5280;margin-top:2px;">Home</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <span class="result-score-num">2</span>
          <span class="result-dash">–</span>
          <span class="result-score-num">1</span>
        </div>
        <div style="text-align:center">
          <div class="result-team-name">Mexico</div>
          <div style="font-size:11px;color:#4a5280;margin-top:2px;">Away</div>
        </div>
      </div>
      <div class="prob-row">
        <div class="prob-pill win">
          <div class="prob-pill-label">Home Win</div>
          <div class="prob-pill-val">58%</div>
        </div>
        <div class="prob-pill">
          <div class="prob-pill-label">Draw</div>
          <div class="prob-pill-val">22%</div>
        </div>
        <div class="prob-pill">
          <div class="prob-pill-label">Away Win</div>
          <div class="prob-pill-val">20%</div>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
// inject click handler for tabs
document.querySelectorAll('.tab').forEach(function(t) {
  t.addEventListener('click', function() {
    document.querySelectorAll('.tab').forEach(function(x){ x.classList.remove('active'); });
    t.classList.add('active');
  });
});
</script>
</body>
</html>"""

html = html.replace("TROPHY_SRC", src)

with open('C:/Users/Nimaa/OneDrive/Desktop/FIFA-WC-2026/.superpowers/brainstorm/1309-1778428415/content/fifa-theme.html','w') as f:
    f.write(html)
print('done:', len(html), 'bytes')
