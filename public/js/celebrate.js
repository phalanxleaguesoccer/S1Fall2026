// Champions pop-up: winner + runner-up with confetti, fireworks and glitter on a canvas. No libraries.
// openChampionsPopup({season, winner, runner, onClose}) where winner/runner = {name, logo, bg, pts, w, d, l, gf, ga, gd}.
function openChampionsPopup(o) {
  if (document.getElementById("cpp")) return;
  var prev = document.activeElement, reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function stats(t) { return "<b>" + t.pts + " pts</b> &middot; " + t.w + "W " + t.d + "D " + t.l + "L &middot; GD " + (t.gd > 0 ? "+" : "") + t.gd; }
  function logo(t) { return '<div class="cpp-logo" style="background:' + esc(t.bg || "#000") + '"><img src="' + esc(t.logo) + '" alt="' + esc(t.name) + ' logo"></div>'; }
  var trophy = '<svg class="cpp-trophy" id="cpp-trophy" viewBox="0 0 64 64" role="img" aria-label="Trophy"><defs><linearGradient id="cppg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff1b8"/><stop offset=".5" stop-color="#e7a93d"/><stop offset="1" stop-color="#a8741c"/></linearGradient></defs>' +
    '<path d="M18 6h28v16c0 9-6 15-14 15s-14-6-14-15V6z" fill="url(#cppg)"/><path d="M18 10H8c0 10 4 16 12 17M46 10h10c0 10-4 16-12 17" fill="none" stroke="url(#cppg)" stroke-width="4" stroke-linecap="round"/>' +
    '<rect x="28" y="36" width="8" height="10" fill="url(#cppg)"/><path d="M20 46h24l3 8H17z" fill="url(#cppg)"/><rect x="14" y="54" width="36" height="5" rx="2" fill="#7a5412"/><path d="M26 12v10" stroke="#fff7d6" stroke-width="2.5" stroke-linecap="round" opacity=".7"/></svg>';
  var html = '<div class="cpp" id="cpp" role="dialog" aria-modal="true" aria-labelledby="cpp-title">' +
    '<canvas class="cpp-fx" id="cpp-fx" aria-hidden="true"></canvas>' +
    '<div class="cpp-box"><button type="button" class="cpp-x" id="cpp-x" aria-label="Close">&times;</button>' +
      '<div class="cpp-kicker">' + esc(o.season || "") + '</div>' + trophy +
      '<h2 class="cpp-title" id="cpp-title">Champions</h2>' +
      '<div class="cpp-win">' + logo(o.winner) + '<div class="cpp-name">' + esc(o.winner.name) + '</div><div class="cpp-role">League winner</div><div class="cpp-stats">' + stats(o.winner) + '</div></div>' +
      '<div class="cpp-run">' + logo(o.runner) + '<div><div class="cpp-role">Runners-up</div><div class="cpp-name">' + esc(o.runner.name) + '</div><div class="cpp-stats">' + stats(o.runner) + '</div></div></div>' +
      '<p class="cpp-thanks">Congratulations, and thank you to every player, captain and supporter.</p>' +
      '<div class="cpp-foot"><a class="cpp-b" href="' + esc(o.standingsHref || "index.html") + '">See final standings</a><button type="button" class="cpp-b alt" id="cpp-close">Close</button></div>' +
    '</div></div>';
  document.body.insertAdjacentHTML("beforeend", html);
  document.body.classList.add("cpp-open");
  var el = document.getElementById("cpp"), cv = document.getElementById("cpp-fx"), ctx = cv.getContext("2d");
  var W = 0, H = 0, dpr = 1, parts = [], rockets = [], sparks = [], stars = [], raf = 0, last = 0, t0 = 0, nextRocket = 0, nextRain = 0, closed = false;
  var COLORS = ["#ffd166", "#ef476f", "#06d6a0", "#118ab2", "#ff9f1c", "#f5f1e6", "#c77dff", "#ff6b6b"];
  function rnd(a, b) { return a + Math.random() * (b - a); }
  function pick(a) { return a[(Math.random() * a.length) | 0]; }
  function size() { dpr = Math.min(window.devicePixelRatio || 1, 2); W = el.clientWidth; H = el.clientHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
  function confetti(x, y, n, spread, power, up) {
    for (var i = 0; i < n; i++) {
      var a = (up ? -Math.PI / 2 : Math.PI / 2) + rnd(-spread, spread), v = rnd(power * .45, power);
      parts.push({ x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, w: rnd(6, 11), h: rnd(3, 6), r: rnd(0, 6.28), vr: rnd(-.25, .25), c: pick(COLORS), ph: rnd(0, 6.28), life: rnd(220, 340), age: 0, glit: Math.random() < .25 });
    }
  }
  function rocket() { var x = rnd(W * .12, W * .88); rockets.push({ x: x, y: H + 10, vy: -rnd(8, 11.5), ty: rnd(H * .12, H * .42), c: pick(COLORS), trail: [] }); }
  function burst(x, y, c) {
    var n = 110, big = Math.random() < .35, col2 = pick(COLORS);
    for (var i = 0; i < n; i++) {
      var a = (i / n) * 6.283 + rnd(-.05, .05), v = (big ? rnd(3.6, 5.8) : rnd(2.2, 4.6)) * (i % 2 ? 1 : .72);
      sparks.push({ px: x, py: y, x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, c: i % 3 ? c : col2, life: rnd(55, 85), age: 0 });
    }
    for (var k = 0; k < 10; k++) stars.push({ x: x + rnd(-40, 40), y: y + rnd(-40, 40), s: rnd(6, 12), life: rnd(25, 45), age: 0, c: "#fff6d2" });
  }
  function star(x, y, s, a, c) {
    ctx.save(); ctx.translate(x, y); ctx.globalAlpha = a; ctx.fillStyle = c; ctx.beginPath();
    for (var i = 0; i < 8; i++) { var r = i % 2 ? s * .22 : s; var ang = i * Math.PI / 4; ctx.lineTo(Math.cos(ang) * r, Math.sin(ang) * r); }
    ctx.closePath(); ctx.fill(); ctx.restore();
  }
  function cannons() { confetti(0, H, 130, .35, 18, true); parts.slice(-130).forEach(function (p) { p.vx = Math.abs(p.vx) + 1; }); confetti(W, H, 130, .35, 18, true); parts.slice(-130).forEach(function (p) { p.vx = -Math.abs(p.vx) - 1; }); }
  function glitterRain() { for (var i = 0; i < 40; i++) { var p = { x: rnd(0, W), y: -10, vx: rnd(-.6, .6), vy: rnd(1.2, 2.6), w: rnd(5, 9), h: rnd(3, 5), r: rnd(0, 6.28), vr: rnd(-.2, .2), c: pick(COLORS), ph: rnd(0, 6.28), life: 360, age: 0, glit: Math.random() < .5 }; parts.push(p); } }
  function frame(now) {
    if (closed) return;
    if (!last) { last = now; t0 = now; }
    var dt = Math.min((now - last) / 16.67, 3); last = now; var el_ms = now - t0;
    if (!document.hidden) {
      if (el_ms < 14000) {
        if (now > nextRocket) { rocket(); if (Math.random() < .5) rocket(); nextRocket = now + rnd(500, 950); }
        if (now > nextRain) { glitterRain(); nextRain = now + 2600; }
      }
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "source-over";
      parts = parts.filter(function (p) { return p.age < p.life && p.y < H + 30; });
      parts.forEach(function (p) {
        p.age += dt; p.vy += .16 * dt; p.vx *= .992; p.vy *= .992; p.x += p.vx * dt + Math.sin(p.age * .08 + p.ph) * .5; p.y += p.vy * dt; p.r += p.vr * dt;
        var fl = Math.abs(Math.cos(p.age * .12 + p.ph)); ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.globalAlpha = Math.min(1, (p.life - p.age) / 40);
        ctx.fillStyle = p.glit ? (fl > .8 ? "#ffffff" : "#ffd166") : p.c; ctx.fillRect(-p.w / 2, -p.h * fl / 2, p.w, Math.max(1, p.h * fl)); ctx.restore();
      });
      rockets = rockets.filter(function (r) {
        r.trail.push([r.x, r.y]); if (r.trail.length > 8) r.trail.shift(); r.y += r.vy * dt; r.vy *= .985; r.x += Math.sin(r.y * .05) * .6;
        ctx.globalCompositeOperation = "lighter";
        r.trail.forEach(function (t, i) { ctx.globalAlpha = i / r.trail.length * .8; ctx.fillStyle = "#ffe9a6"; ctx.fillRect(t[0] - 1.5, t[1], 3, 3); });
        if (r.y <= r.ty || r.vy > -1.2) { burst(r.x, r.y, r.c); return false; } return true;
      });
      ctx.globalCompositeOperation = "lighter";
      sparks = sparks.filter(function (s) { return s.age < s.life; });
      sparks.forEach(function (s) {
        s.age += dt; s.px = s.x; s.py = s.y; s.vy += .05 * dt; s.vx *= .985; s.vy *= .985; s.x += s.vx * dt; s.y += s.vy * dt;
        var a = Math.max(0, 1 - s.age / s.life); ctx.globalAlpha = a; ctx.strokeStyle = s.c; ctx.lineWidth = 2.6 * (.5 + a); ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(s.px - s.vx * 1.6, s.py - s.vy * 1.6); ctx.lineTo(s.x, s.y); ctx.stroke();
        ctx.fillStyle = "#fff"; ctx.globalAlpha = a * .8; ctx.beginPath(); ctx.arc(s.x, s.y, 1.4, 0, 6.283); ctx.fill();
      });
      stars = stars.filter(function (s) { return s.age < s.life; });
      stars.forEach(function (s) { s.age += dt; var a = Math.sin(Math.PI * s.age / s.life); star(s.x, s.y, s.s * (.6 + a * .6), a, s.c); });
      ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
    }
    if (el_ms > 14000 && !parts.length && !rockets.length && !sparks.length && !stars.length) { ctx.clearRect(0, 0, W, H); return; }
    raf = requestAnimationFrame(frame);
  }
  function celebrate() { if (reduce) return; cancelAnimationFrame(raf); last = 0; nextRocket = 0; nextRain = 0; cannons(); rocket(); raf = requestAnimationFrame(frame); }
  function onResize() { size(); }
  function close() {
    closed = true; cancelAnimationFrame(raf); document.removeEventListener("keydown", onKey); window.removeEventListener("resize", onResize);
    el.remove(); document.body.classList.remove("cpp-open");
    try { if (prev && prev.focus) prev.focus(); } catch (e) {}
    if (o.onClose) o.onClose();
  }
  function onKey(e) {
    if (e.key === "Escape") { close(); return; }
    if (e.key === "Tab") { var f = el.querySelectorAll("a[href],button"); if (!f.length) return; var a = f[0], z = f[f.length - 1];
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); } else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); } }
  }
  document.addEventListener("keydown", onKey); window.addEventListener("resize", onResize);
  document.getElementById("cpp-x").addEventListener("click", close);
  document.getElementById("cpp-close").addEventListener("click", close);
  document.getElementById("cpp-trophy").addEventListener("click", function () { closed = false; celebrate(); });
  el.addEventListener("click", function (e) { if (e.target === el) close(); });
  size(); celebrate();
  document.getElementById("cpp-x").focus();
  return { replay: function () { closed = false; celebrate(); }, close: close };
}
