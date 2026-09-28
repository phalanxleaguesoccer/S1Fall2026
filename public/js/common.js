// Shared header/footer injection + small helpers used across all pages.

function renderHeader(activePage) {
  var links = [
    ["index.html", "Standings"],
    ["teams.html", "Teams"],
    ["players.html", "Players"],
    ["matches.html", "Matches"],
    ["admin/login.html", "Admin"]
  ];
  var nav = links.map(function (l) {
    var active = activePage === l[0] ? " active" : "";
    return '<a class="' + active.trim() + '" href="' + l[0] + '">' + l[1] + "</a>";
  }).join("");

  document.body.insertAdjacentHTML(
    "afterbegin",
    '<header class="site-header"><div class="container">' +
      '<a class="brand" href="index.html"><span class="crest">PLS</span> Phalanx League Soccer</span></a>' +
      '<nav class="main-nav">' + nav + "</nav>" +
      "</div></header>"
  );
}

function renderFooter() {
  document.body.insertAdjacentHTML(
    "beforeend",
    '<footer class="site-footer">Phalanx League Soccer | <span id="footer-season">…</span> | 6-A-side | <span id="footer-views">…</span></footer>'
  );

  // Fill in the current season's name once Supabase is ready.
  if (window.sb) {
    getCurrentSeason().then(function (season) {
      var el = document.getElementById("footer-season");
      if (el) el.textContent = season ? season.name : "—";
    });
    trackPageView("site").then(function (count) {
      var el = document.getElementById("footer-views");
      if (el) el.textContent = formatViewCount(count) + " site-wide";
    });
  }
}

// Renders a breadcrumb trail right under the header so people can jump back
// to any ancestor page without relying on the browser's back button.
// `crumbs` is an array of { label, href } — href is omitted (or null) on the
// last entry, which renders as plain (non-link) text for the current page.
function renderBreadcrumbs(crumbs) {
  var html = crumbs.map(function (c, i) {
    var isLast = i === crumbs.length - 1;
    var piece = (!isLast && c.href)
      ? '<a href="' + escapeHtml(c.href) + '">' + escapeHtml(c.label) + "</a>"
      : '<span class="current"' + (isLast ? ' id="crumb-current"' : '') + '>' + escapeHtml(c.label) + "</span>";
    return i === 0 ? piece : '<span class="sep">/</span>' + piece;
  }).join("");

  document.body.insertAdjacentHTML(
    "afterbegin",
    '<nav class="breadcrumbs">' + html + "</nav>"
  );

  // Header is inserted afterbegin too (see renderHeader), and is always
  // called before renderBreadcrumbs on every page, so the breadcrumb nav
  // (inserted after the header exists) ends up directly below it.
  var header = document.querySelector(".site-header");
  var nav = document.querySelector(".breadcrumbs");
  if (header && nav && header.nextSibling !== nav) {
    header.insertAdjacentElement("afterend", nav);
  }
}

function formatViewCount(count) {
  if (count === null || count === undefined) return "—";
  return count.toLocaleString() + (count === 1 ? " view" : " views");
}

// Counts every page load as a view (people revisit the same player/team page
// multiple times a day for different research, and each of those should
// count), then returns the current total.
async function trackPageView(pageKey) {
  try {
    var incRes = await window.sb.rpc("increment_page_view", { p_key: pageKey });
    if (!incRes.error && typeof incRes.data === "number") return incRes.data;
  } catch (err) {
    // RPC can fail (offline, etc.) — fall through to a plain read so the
    // count still displays even if this particular visit didn't increment.
  }
  try {
    var res = await window.sb.from("page_views").select("view_count").eq("page_key", pageKey).maybeSingle();
    return res.data ? res.data.view_count : null;
  } catch (err) {
    return null;
  }
}

function fixHref(activePage) {
  // Pages under /admin/ need "../" prefixes for nav links; patched here so
  // renderHeader() can stay simple for top-level pages.
  if (window.IN_ADMIN_DIR) {
    document.querySelectorAll("nav.main-nav a").forEach(function (a) {
      var href = a.getAttribute("href");
      if (href.indexOf("admin/") !== 0 && href !== "admin/login.html") {
        a.setAttribute("href", "../" + href);
      }
    });
    document.querySelector(".brand").setAttribute("href", "../index.html");
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function qs(name) {
  var params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function showError(el, message) {
  el.textContent = message;
  el.className = "error-msg";
}
function showSuccess(el, message) {
  el.textContent = message;
  el.className = "success-msg";
}

// Returns { data: currentSeason } for the season flagged is_current = true.
async function getCurrentSeason() {
  var res = await window.sb.from("seasons").select("*").eq("is_current", true).limit(1).single();
  return res.data;
}
