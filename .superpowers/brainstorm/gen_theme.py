import base64

with open('C:/Users/Nimaa/OneDrive/Desktop/FIFA-WC-2026/.superpowers/brainstorm/1309-1778428415/content/trophy_nobg.png','rb') as f:
    b64 = base64.b64encode(f.read()).decode()

src = f"data:image/png;base64,{b64}"

html = """<h2>Choose your World Cup theme style</h2>
<p class="subtitle">Full redesign — pick the visual direction that feels right</p>

<style>
  .cards { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-top: 20px; }
  .card { border: 2px solid #1e2d4a; border-radius: 16px; overflow: hidden; cursor: pointer; transition: border-color 0.2s, transform 0.2s; }
  .card:hover { border-color: #d4af37; transform: translateY(-3px); }
  .card.selected { border-color: #d4af37; box-shadow: 0 0 24px rgba(212,175,55,0.4); }
  .card-preview { height: 320px; position: relative; overflow: hidden; display: flex; flex-direction: column; }
  .card-body { padding: 14px 16px; background: #0d1428; }
  .card-body h3 { color: #f1f5f9; margin: 0 0 5px; font-size: 14px; }
  .card-body p  { color: #94a3b8; font-size: 12px; margin: 0; line-height: 1.5; }
  .tag { font-size: 10px; background: #1e2d4a; color: #d4af37; border-radius: 4px; padding: 2px 7px; display: inline-block; margin-top: 7px; }

  /* A: Stadium Night */
  .a-header { background: linear-gradient(180deg,#0a0e1a 0%,#0d2044 60%,#0a0e1a 100%); padding: 18px 16px 14px; display: flex; flex-direction: column; align-items: center; gap: 6px; position: relative; border-bottom: 1px solid #1e3a6a; }
  .a-header::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 120%, rgba(0,168,107,0.13) 0%, transparent 70%); }
  .a-trophy { height: 90px; object-fit: contain; filter: drop-shadow(0 0 20px rgba(212,175,55,0.9)); animation: float 3s ease-in-out infinite; }
  .a-title { color: #fff; font-size: 11px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; position: relative; }
  .a-sub   { color: #64748b; font-size: 9px; position: relative; }
  .a-tabs  { display: flex; border-bottom: 1px solid #1e2d4a; background: #0d1428; }
  .a-tab   { padding: 7px 12px; font-size: 10px; color: #64748b; border-bottom: 2px solid transparent; }
  .a-tab.on { color: #d4af37; border-bottom-color: #d4af37; }
  .a-body  { background: #0a0e1a; flex: 1; padding: 10px; display: flex; flex-direction: column; gap: 6px; }
  .a-card  { background: #0d1428; border: 1px solid #1e2d4a; border-radius: 8px; padding: 8px 10px; }

  /* B: Bold Red & Gold */
  .b-header { background: linear-gradient(135deg,#7f1d1d 0%,#450a0a 50%,#1a0a00 100%); padding: 18px 16px 14px; display: flex; flex-direction: column; align-items: center; gap: 6px; border-bottom: 2px solid #d4af37; }
  .b-trophy { height: 90px; object-fit: contain; filter: drop-shadow(0 0 22px rgba(212,175,55,1)); animation: float 3s ease-in-out infinite; }
  .b-title { color: #fbbf24; font-size: 11px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; }
  .b-sub   { color: #fca5a5; font-size: 9px; }
  .b-tabs  { display: flex; border-bottom: 2px solid #d4af37; background: #1a0a00; }
  .b-tab   { padding: 7px 12px; font-size: 10px; color: #92400e; border-bottom: 2px solid transparent; }
  .b-tab.on { color: #fbbf24; border-bottom-color: #fbbf24; margin-bottom: -2px; }
  .b-body  { background: #0c0a00; flex: 1; padding: 10px; display: flex; flex-direction: column; gap: 6px; }
  .b-card  { background: #1a0e00; border: 1px solid #78350f; border-radius: 8px; padding: 8px 10px; }

  /* C: Glassmorphism Premium */
  .c-header { background: linear-gradient(160deg,#0f1d38 0%,#0a0e1a 100%); padding: 18px 16px 14px; display: flex; flex-direction: column; align-items: center; gap: 6px; position: relative; border-bottom: 1px solid rgba(212,175,55,0.2); }
  .c-header::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 0%, rgba(212,175,55,0.12) 0%, transparent 65%); }
  .c-trophy { height: 90px; object-fit: contain; filter: drop-shadow(0 0 24px rgba(212,175,55,1)); animation: float 3s ease-in-out infinite; }
  .c-title { color: #fff; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; position: relative; }
  .c-sub   { color: #94a3b8; font-size: 9px; position: relative; }
  .c-tabs  { display: flex; border-bottom: 1px solid rgba(255,255,255,0.08); background: rgba(13,20,40,0.95); }
  .c-tab   { padding: 7px 12px; font-size: 10px; color: #475569; border-bottom: 2px solid transparent; }
  .c-tab.on { color: #d4af37; border-bottom-color: #d4af37; }
  .c-body  { background: linear-gradient(180deg,#0d1428,#080c18); flex: 1; padding: 10px; display: flex; flex-direction: column; gap: 6px; }
  .c-card  { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 8px 10px; }

  /* shared row styles */
  .row-label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
  .row-teams { display: flex; align-items: center; justify-content: space-between; }
  .team-name { font-size: 10px; font-weight: 700; }
  .vs-label  { font-size: 9px; }
  .bar       { height: 4px; border-radius: 2px; margin-top: 6px; overflow: hidden; }
  .bar-fill  { height: 100%; border-radius: 2px; }

  .a-row-label { color: #94a3b8; } .a-team { color: #f1f5f9; } .a-vs { color: #475569; }
  .a-bar-bg { background: #1e2d4a; } .a-bar-fill { background: linear-gradient(90deg,#d4af37,#f5d060); }
  .b-row-label { color: #92400e; } .b-team { color: #fef3c7; } .b-vs { color: #78350f; }
  .b-bar-bg { background: #78350f; } .b-bar-fill { background: linear-gradient(90deg,#d97706,#fbbf24); }
  .c-row-label { color: #64748b; } .c-team { color: #f1f5f9; } .c-vs { color: #334155; }
  .c-bar-bg { background: rgba(255,255,255,0.06); } .c-bar-fill { background: linear-gradient(90deg,#d4af37,#f5d060); }

  @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-12px)} }
</style>

<div class="cards">

  <div class="card" data-choice="a" onclick="toggleSelect(this)">
    <div class="card-preview">
      <div class="a-header">
        <img class="a-trophy" src="TROPHY_SRC" alt="trophy"/>
        <div class="a-title">FIFA WC 2026 Predictor</div>
        <div class="a-sub">AI-powered match predictions</div>
      </div>
      <div class="a-tabs"><div class="a-tab on">Group Stage</div><div class="a-tab">Predict Match</div></div>
      <div class="a-body">
        <div class="a-card">
          <div class="row-label a-row-label">Group A · Match 1</div>
          <div class="row-teams"><span class="team-name a-team">USA</span><span class="vs-label a-vs">vs</span><span class="team-name a-team">Mexico</span></div>
          <div class="bar a-bar-bg"><div class="bar-fill a-bar-fill" style="width:62%"></div></div>
        </div>
        <div class="a-card">
          <div class="row-label a-row-label">Group B · Match 1</div>
          <div class="row-teams"><span class="team-name a-team">Brazil</span><span class="vs-label a-vs">vs</span><span class="team-name a-team">Argentina</span></div>
          <div class="bar a-bar-bg"><div class="bar-fill a-bar-fill" style="width:45%"></div></div>
        </div>
      </div>
    </div>
    <div class="card-body">
      <h3>A — Stadium Night</h3>
      <p>Deep navy + green pitch glow. Feels like a floodlit stadium at night. Sporty and clean.</p>
      <span class="tag">Classic football</span>
    </div>
  </div>

  <div class="card" data-choice="b" onclick="toggleSelect(this)">
    <div class="card-preview">
      <div class="b-header">
        <img class="b-trophy" src="TROPHY_SRC" alt="trophy"/>
        <div class="b-title">FIFA WC 2026 Predictor</div>
        <div class="b-sub">AI-powered match predictions</div>
      </div>
      <div class="b-tabs"><div class="b-tab on">Group Stage</div><div class="b-tab">Predict Match</div></div>
      <div class="b-body">
        <div class="b-card">
          <div class="row-label b-row-label">Group A · Match 1</div>
          <div class="row-teams"><span class="team-name b-team">USA</span><span class="vs-label b-vs">vs</span><span class="team-name b-team">Mexico</span></div>
          <div class="bar b-bar-bg"><div class="bar-fill b-bar-fill" style="width:62%"></div></div>
        </div>
        <div class="b-card">
          <div class="row-label b-row-label">Group B · Match 1</div>
          <div class="row-teams"><span class="team-name b-team">Brazil</span><span class="vs-label b-vs">vs</span><span class="team-name b-team">Argentina</span></div>
          <div class="bar b-bar-bg"><div class="bar-fill b-bar-fill" style="width:45%"></div></div>
        </div>
      </div>
    </div>
    <div class="card-body">
      <h3>B — Bold Red & Gold</h3>
      <p>Deep crimson + gold. Tournament-poster energy. High contrast and very attention-grabbing.</p>
      <span class="tag">Bold & dramatic</span>
    </div>
  </div>

  <div class="card" data-choice="c" onclick="toggleSelect(this)">
    <div class="card-preview">
      <div class="c-header">
        <img class="c-trophy" src="TROPHY_SRC" alt="trophy"/>
        <div class="c-title">FIFA WC 2026 Predictor</div>
        <div class="c-sub">AI-powered match predictions</div>
      </div>
      <div class="c-tabs"><div class="c-tab on">Group Stage</div><div class="c-tab">Predict Match</div></div>
      <div class="c-body">
        <div class="c-card">
          <div class="row-label c-row-label">Group A · Match 1</div>
          <div class="row-teams"><span class="team-name c-team">USA</span><span class="vs-label c-vs">vs</span><span class="team-name c-team">Mexico</span></div>
          <div class="bar c-bar-bg"><div class="bar-fill c-bar-fill" style="width:62%"></div></div>
        </div>
        <div class="c-card">
          <div class="row-label c-row-label">Group B · Match 1</div>
          <div class="row-teams"><span class="team-name c-team">Brazil</span><span class="vs-label c-vs">vs</span><span class="team-name c-team">Argentina</span></div>
          <div class="bar c-bar-bg"><div class="bar-fill c-bar-fill" style="width:45%"></div></div>
        </div>
      </div>
    </div>
    <div class="card-body">
      <h3>C — Glassmorphism Premium</h3>
      <p>Dark navy + frosted glass cards + gold accents. Sleek, modern, premium app feel.</p>
      <span class="tag">Modern premium</span>
    </div>
  </div>

</div>
<p class="subtitle" style="margin-top:18px;font-size:12px;">Trophy floats in all three. Click your favourite or tell me in the terminal.</p>"""

html = html.replace("TROPHY_SRC", src)

with open('C:/Users/Nimaa/OneDrive/Desktop/FIFA-WC-2026/.superpowers/brainstorm/1309-1778428415/content/theme-style.html','w') as f:
    f.write(html)
print('done:', len(html), 'bytes')
