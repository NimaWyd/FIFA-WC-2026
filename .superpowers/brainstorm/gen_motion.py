import base64

with open('C:/Users/Nimaa/OneDrive/Desktop/FIFA-WC-2026/.superpowers/brainstorm/1309-1778428415/content/trophy_nobg.png','rb') as f:
    src = 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Trophy Motion Options</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#090b14; color:#fff; font-family:'Inter','Helvetica Neue',Arial,sans-serif; padding: 24px; }

  h2 { font-size: 20px; font-weight: 800; color: #fff; margin-bottom: 6px; }
  .subtitle { color: #8b93b8; font-size: 13px; margin-bottom: 24px; }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }

  .option {
    background: #0e1020;
    border: 2px solid #1e2340;
    border-radius: 16px;
    overflow: hidden;
    cursor: pointer;
    transition: border-color 0.2s, transform 0.2s;
  }
  .option:hover { border-color: #1a3fff; transform: translateY(-2px); }
  .option.selected { border-color: #f5c842; box-shadow: 0 0 24px rgba(245,200,66,0.3); }

  .preview {
    height: 240px;
    background: radial-gradient(ellipse at 50% 0%, #0d1d8a 0%, #090b14 60%);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 12px; position: relative; overflow: hidden;
  }
  .preview::after {
    content: '';
    position: absolute; inset: 0;
    background: repeating-linear-gradient(-45deg, rgba(255,255,255,0.012) 0px, rgba(255,255,255,0.012) 1px, transparent 1px, transparent 28px);
    pointer-events: none;
  }
  .trophy { height: 140px; object-fit: contain; }
  .preview-label { font-size: 11px; color: #8b93b8; font-weight: 600; letter-spacing: 0.5px; position: relative; z-index:1; }

  .info { padding: 16px 18px; }
  .info h3 { font-size: 14px; font-weight: 800; margin-bottom: 5px; }
  .info p  { font-size: 12px; color: #8b93b8; line-height: 1.5; }
  .tag { font-size: 10px; background: #151829; color: #1a3fff; border: 1px solid #1e2340; border-radius: 4px; padding: 2px 8px; display: inline-block; margin-top: 8px; font-weight: 600; }

  /* A: Float */
  .anim-float {
    filter: drop-shadow(0 0 30px rgba(245,200,66,0.8));
    animation: float 3s ease-in-out infinite;
  }
  @keyframes float { 0%,100%{transform:translateY(0px)} 50%{transform:translateY(-22px)} }

  /* B: Mouse follow — handled by JS */
  .anim-mouse {
    filter: drop-shadow(0 0 30px rgba(26,63,255,0.8));
    transition: transform 0.15s ease-out;
  }

  /* C: 3D spin */
  .anim-spin {
    filter: drop-shadow(0 0 30px rgba(245,200,66,0.7));
    animation: spin3d 4s linear infinite;
  }
  @keyframes spin3d {
    0%   { transform: perspective(400px) rotateY(0deg) scale(1); filter: drop-shadow(0 0 30px rgba(245,200,66,0.7)); }
    25%  { transform: perspective(400px) rotateY(90deg) scale(0.85); filter: drop-shadow(0 0 10px rgba(245,200,66,0.3)); }
    50%  { transform: perspective(400px) rotateY(180deg) scale(1); filter: drop-shadow(0 0 30px rgba(245,200,66,0.7)); }
    75%  { transform: perspective(400px) rotateY(270deg) scale(0.85); filter: drop-shadow(0 0 10px rgba(245,200,66,0.3)); }
    100% { transform: perspective(400px) rotateY(360deg) scale(1); filter: drop-shadow(0 0 30px rgba(245,200,66,0.7)); }
  }

  /* D: Float + tilt — handled by JS + CSS */
  .anim-combo {
    filter: drop-shadow(0 0 30px rgba(245,200,66,0.85));
    animation: float-combo 3s ease-in-out infinite;
    transition: transform 0.12s ease-out;
  }
  @keyframes float-combo { 0%,100%{transform:translateY(0px)} 50%{transform:translateY(-20px)} }
</style>
</head>
<body>

<h2>How should the trophy move?</h2>
<p class="subtitle">Hover over each preview to interact — click to select your favourite</p>

<div class="grid">

  <!-- A: Float -->
  <div class="option" data-choice="a" onclick="selectOption(this)">
    <div class="preview" id="prev-a">
      <img class="trophy anim-float" src="TROPHY_SRC" alt="trophy"/>
      <span class="preview-label">Always animating</span>
    </div>
    <div class="info">
      <h3>A — Gentle Float</h3>
      <p>Trophy softly bobs up and down continuously, like it's hovering in zero gravity. Calm and elegant.</p>
      <span class="tag">Smooth &amp; elegant</span>
    </div>
  </div>

  <!-- B: Mouse follow -->
  <div class="option" data-choice="b" onclick="selectOption(this)">
    <div class="preview" id="prev-b">
      <img class="trophy anim-mouse" id="trophy-b" src="TROPHY_SRC" alt="trophy"/>
      <span class="preview-label">Move your mouse over this card</span>
    </div>
    <div class="info">
      <h3>B — Mouse Parallax</h3>
      <p>Trophy tilts and shifts to follow your cursor as you move around the hero. Feels alive and interactive.</p>
      <span class="tag">Interactive</span>
    </div>
  </div>

  <!-- C: 3D Spin -->
  <div class="option" data-choice="c" onclick="selectOption(this)">
    <div class="preview" id="prev-c">
      <img class="trophy anim-spin" src="TROPHY_SRC" alt="trophy"/>
      <span class="preview-label">Always rotating</span>
    </div>
    <div class="info">
      <h3>C — 3D Showcase Spin</h3>
      <p>Trophy rotates slowly on its Y-axis like it's on a display pedestal. Bold and dramatic.</p>
      <span class="tag">Dramatic showcase</span>
    </div>
  </div>

  <!-- D: Float + tilt combo -->
  <div class="option" data-choice="d" onclick="selectOption(this)">
    <div class="preview" id="prev-d">
      <img class="trophy anim-combo" id="trophy-d" src="TROPHY_SRC" alt="trophy"/>
      <span class="preview-label">Float + move your mouse here</span>
    </div>
    <div class="info">
      <h3>D — Float + Mouse Tilt</h3>
      <p>Combines the gentle float with a subtle tilt toward your cursor. Dynamic but not distracting. Best of both.</p>
      <span class="tag">Best of both</span>
    </div>
  </div>

</div>

<p style="margin-top:20px; font-size:12px; color:#4a5280; text-align:center;">Click a card to select or tell me your pick in the terminal.</p>

<script>
  // Selection
  function selectOption(el) {
    document.querySelectorAll('.option').forEach(function(o){ o.classList.remove('selected'); });
    el.classList.add('selected');
    if (window.sendSelection) window.sendSelection(el.dataset.choice, el.querySelector('h3').textContent);
  }

  // B: Mouse parallax
  var prevB = document.getElementById('prev-b');
  var trophyB = document.getElementById('trophy-b');
  prevB.addEventListener('mousemove', function(e) {
    var rect = prevB.getBoundingClientRect();
    var cx = rect.left + rect.width / 2;
    var cy = rect.top + rect.height / 2;
    var dx = (e.clientX - cx) / (rect.width / 2);
    var dy = (e.clientY - cy) / (rect.height / 2);
    trophyB.style.transform = 'perspective(400px) rotateY(' + (dx * 20) + 'deg) rotateX(' + (-dy * 15) + 'deg) translateX(' + (dx * 14) + 'px) translateY(' + (dy * 8) + 'px)';
  });
  prevB.addEventListener('mouseleave', function() {
    trophyB.style.transform = 'perspective(400px) rotateY(0deg) rotateX(0deg)';
  });

  // D: Float + tilt combo
  var prevD = document.getElementById('prev-d');
  var trophyD = document.getElementById('trophy-d');
  var floatOffset = 0;
  var mouseX = 0, mouseY = 0;
  var hasMouseD = false;

  prevD.addEventListener('mousemove', function(e) {
    hasMouseD = true;
    var rect = prevD.getBoundingClientRect();
    var cx = rect.left + rect.width / 2;
    var cy = rect.top + rect.height / 2;
    mouseX = (e.clientX - cx) / (rect.width / 2);
    mouseY = (e.clientY - cy) / (rect.height / 2);
  });
  prevD.addEventListener('mouseleave', function() {
    hasMouseD = false;
    mouseX = 0; mouseY = 0;
  });

  var startTime = Date.now();
  function animateD() {
    var t = (Date.now() - startTime) / 1000;
    var floatY = -Math.sin(t * Math.PI * 2 / 3) * 20;
    var tiltX = hasMouseD ? -mouseY * 14 : 0;
    var tiltY = hasMouseD ? mouseX * 18 : 0;
    var tx    = hasMouseD ? mouseX * 12 : 0;
    trophyD.style.animation = 'none';
    trophyD.style.transform =
      'perspective(400px) rotateX(' + tiltX + 'deg) rotateY(' + tiltY + 'deg) translateX(' + tx + 'px) translateY(' + floatY + 'px)';
    requestAnimationFrame(animateD);
  }
  animateD();
</script>
</body>
</html>"""

html = html.replace("TROPHY_SRC", src)

with open('C:/Users/Nimaa/OneDrive/Desktop/FIFA-WC-2026/.superpowers/brainstorm/1309-1778428415/content/trophy-motion.html','w', encoding='utf-8') as f:
    f.write(html)
print('done:', len(html), 'bytes')
