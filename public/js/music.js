// Theme-music players for the Branding & Sponsors page. One track plays at a time; playback only starts from a tap (browsers block autoplay).
function initThemeMusic() {
  var tracks = Array.prototype.slice.call(document.querySelectorAll(".tm-track"));
  function fmt(s) { if (!isFinite(s)) return "0:00"; var m = Math.floor(s / 60), r = Math.floor(s % 60); return m + ":" + (r < 10 ? "0" : "") + r; }
  tracks.forEach(function (t) {
    var a = t.querySelector("audio"), btn = t.querySelector(".tm-play"), seek = t.querySelector(".tm-seek"), time = t.querySelector(".tm-time");
    function paint() {
      time.textContent = fmt(a.currentTime) + " / " + fmt(a.duration);
      if (a.duration) seek.value = String(Math.round(a.currentTime / a.duration * 1000));
    }
    btn.addEventListener("click", function () {
      if (a.paused) {
        tracks.forEach(function (o) { var oa = o.querySelector("audio"); if (oa !== a && !oa.paused) oa.pause(); });
        var p = a.play(); if (p && p.catch) p.catch(function () {});
      } else a.pause();
    });
    a.addEventListener("play", function () { btn.classList.add("playing"); btn.setAttribute("aria-label", "Pause"); t.classList.add("on"); });
    a.addEventListener("pause", function () { btn.classList.remove("playing"); btn.setAttribute("aria-label", "Play"); t.classList.remove("on"); });
    a.addEventListener("ended", function () { a.currentTime = 0; paint(); });
    a.addEventListener("timeupdate", paint);
    a.addEventListener("loadedmetadata", paint);
    seek.addEventListener("input", function () { if (a.duration) a.currentTime = a.duration * seek.value / 1000; });
  });
}
