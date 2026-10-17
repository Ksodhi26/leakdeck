/* LeakDeck front-end. No build step, no dependencies.
   - Launches and rumors lists are pre-rendered in the HTML (SEO + no-JS); this file filters them.
   - News is loaded from news.json (refreshed daily by the GitHub Action).
   Fill these in when ready (both empty = nothing loads, no tracking, no signup form): */
var CF_ANALYTICS_TOKEN = "";   // Cloudflare Web Analytics token (cookieless). Dashboard > Web Analytics > add site.
var EMAIL_SIGNUP_URL = "";     // Form action URL from your email provider (Buttondown, Beehiiv, MailerLite, ...)

(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var CATS = { apple: "Apple", android: "Google / Android", samsung: "Samsung", ai: "AI", gaming: "Gaming", chips: "Chips & PCs", evs: "EVs" };

  /* ---------- analytics (only when a token is set) ---------- */
  if (CF_ANALYTICS_TOKEN) {
    var s = document.createElement("script"); s.defer = true; s.src = "https://static.cloudflareinsights.com/beacon.min.js";
    s.setAttribute("data-cf-beacon", JSON.stringify({ token: CF_ANALYTICS_TOKEN })); document.head.appendChild(s);
  }

  /* ---------- mode toggle ---------- */
  var tgl = $("#mode-toggle");
  function paintToggle() { if (tgl) { var l = document.documentElement.getAttribute("data-mode") === "light"; tgl.textContent = l ? "🌙" : "☀️"; tgl.setAttribute("aria-label", l ? "Switch to dark mode" : "Switch to light mode"); } }
  if (tgl) { paintToggle(); tgl.addEventListener("click", function () {
    var n = document.documentElement.getAttribute("data-mode") === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-mode", n); try { localStorage.setItem("ld-mode", n); } catch (e) {} paintToggle(); }); }

  /* ---------- helpers ---------- */
  function esc(t) { return String(t).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function ago(iso) {
    var d = (Date.now() - new Date(iso).getTime()) / 1000; if (isNaN(d)) return "";
    if (d < 90) return "just now"; if (d < 3600) return Math.round(d / 60) + " min ago";
    if (d < 86400) return Math.round(d / 3600) + " hr ago"; var days = Math.round(d / 86400);
    return days === 1 ? "yesterday" : days + " days ago";
  }
  function daysUntil(dateStr) {
    var a = new Date(dateStr + "T00:00:00"), n = new Date(); n.setHours(0, 0, 0, 0);
    return Math.round((a - n) / 86400000);
  }
  function countLabel(n) { return n === 0 ? "Today" : n === 1 ? "Tomorrow" : n > 1 ? "in " + n + " days" : ""; }
  function param(k) { return new URLSearchParams(location.search).get(k) || ""; }

  /* ---------- countdown labels (day-precision launches) ---------- */
  $$("[data-count]").forEach(function (el) { var n = daysUntil(el.getAttribute("data-count")); el.textContent = countLabel(n); });

  /* ---------- filtering for pre-rendered lists ---------- */
  function setupList(listSel, itemSel, opts) {
    var list = $(listSel); if (!list) return;
    var items = $$(itemSel, list), state = { cat: "", f: "", q: param("q").toLowerCase() };
    var qBox = $("#filter-q"); if (qBox && state.q) qBox.value = param("q");
    var empty = $("#empty");
    function apply() {
      var shown = 0;
      items.forEach(function (el) {
        var ok = true;
        if (state.cat && (" " + el.getAttribute("data-cats") + " ").indexOf(" " + state.cat + " ") < 0) ok = false;
        if (state.f && !opts.match(el, state.f)) ok = false;
        if (state.q && el.getAttribute("data-text").indexOf(state.q) < 0) ok = false;
        el.hidden = !ok; if (ok) shown++;
      });
      $$(".month, .group", list).forEach(function (h) {
        var n = h.nextElementSibling, any = false;
        while (n && !n.classList.contains("month") && !n.classList.contains("group")) { if (n.querySelector && n.querySelector(itemSel + ":not([hidden])") || (n.matches && n.matches(itemSel + ":not([hidden])"))) any = true; n = n.nextElementSibling; }
        h.hidden = !any;
      });
      if (empty) empty.hidden = shown > 0;
    }
    $$("[data-cat]").forEach(function (b) { b.addEventListener("click", function () {
      var v = b.getAttribute("data-cat"); state.cat = state.cat === v ? "" : v;
      $$("[data-cat]").forEach(function (x) { x.setAttribute("aria-pressed", String(x.getAttribute("data-cat") === state.cat)); }); apply(); }); });
    $$("[data-f]").forEach(function (b) { b.addEventListener("click", function () {
      var v = b.getAttribute("data-f"); state.f = state.f === v ? "" : v;
      $$("[data-f]").forEach(function (x) { x.setAttribute("aria-pressed", String(x.getAttribute("data-f") === state.f)); }); apply(); }); });
    if (qBox) qBox.addEventListener("input", function () { state.q = qBox.value.trim().toLowerCase(); apply(); });
    var h = (location.hash || "").replace("#", "");
    if (h && CATS[h]) { var b = $('[data-cat="' + h + '"]'); if (b) b.click(); }
    apply();
  }
  setupList("#launch-list", ".launch", { match: function (el, f) {
    var s = el.getAttribute("data-status"); return f === "confirmed" ? s === "Confirmed" : f === "expected" ? (s === "Expected" || s === "Estimated") : f === "released" ? s === "Released" : true; } });
  setupList("#rumor-list", ".rumor-card", { match: function (el, f) { return el.getAttribute("data-rating").toLowerCase() === f || (f === "resolved" && el.getAttribute("data-status") === "Resolved"); } });

  /* ---------- add to calendar (.ics) ---------- */
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-ics]"); if (!b) return;
    var d = b.getAttribute("data-ics"), name = b.getAttribute("data-name"), url = b.getAttribute("data-url");
    var end = new Date(d + "T00:00:00Z"); end.setUTCDate(end.getUTCDate() + 1);
    var f = function (x) { return x.replace(/-/g, ""); };
    var ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//LeakDeck//EN", "BEGIN:VEVENT",
      "UID:" + d + "-" + name.replace(/\W+/g, "-") + "@leakdeck", "DTSTAMP:" + new Date().toISOString().replace(/[-:]/g, "").split(".")[0] + "Z",
      "DTSTART;VALUE=DATE:" + f(d), "DTEND;VALUE=DATE:" + f(end.toISOString().slice(0, 10)),
      "SUMMARY:" + name.replace(/[,;]/g, " "), "DESCRIPTION:Details: " + url, "END:VEVENT", "END:VCALENDAR"].join("\r\n");
    var a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar" }));
    a.download = name.replace(/\W+/g, "-").toLowerCase() + ".ics"; document.body.appendChild(a); a.click(); a.remove();
  });

  /* ---------- news ---------- */
  var newsBox = $("#news-list");
  if (newsBox) {
    var limit = parseInt(newsBox.getAttribute("data-limit") || "40", 10), page = limit, all = [], st = { cat: "", q: param("q").toLowerCase(), rumor: false };
    var more = $("#news-more"), status = $("#news-status"), qBox2 = $("#filter-q");
    if (qBox2 && param("q")) qBox2.value = param("q");
    var render = function () {
      var rows = all.filter(function (i) {
        if (st.cat && i.categories.indexOf(st.cat) < 0) return false;
        if (st.rumor && !i.rumor) return false;
        if (st.q && (i.title + " " + i.source + " " + (i.summary || "")).toLowerCase().indexOf(st.q) < 0) return false;
        return true; });
      newsBox.innerHTML = rows.slice(0, page).map(function (i) {
        return '<li><a class="t" href="' + esc(i.url) + '" rel="noopener nofollow" target="_blank">' + esc(i.title) + '</a>' +
          (i.summary ? '<span class="sum">' + esc(i.summary) + '</span>' : '') +
          '<span class="m"><span class="src">' + esc(i.source) + '</span><span>' + ago(i.published) + '</span>' +
          (i.rumor ? '<span class="badge-rumor">Rumor mill</span>' : '') +
          i.categories.slice(0, 3).map(function (c) { return '<span class="pill">' + esc(CATS[c] || c) + '</span>'; }).join("") + '</span></li>'; }).join("") ||
        '<li class="empty">No headlines match. Try another filter.</li>';
      if (more) more.hidden = rows.length <= page;
    };
    fetch("news.json", { cache: "no-cache" }).then(function (r) { return r.json(); }).then(function (d) {
      all = d.items || []; if (status) status.textContent = "Updated " + ago(d.updated) + " from " + (d.sources || []).length + " sources";
      render();
    }).catch(function () { if (status) status.textContent = "Could not load headlines right now."; });
    $$("[data-ncat]").forEach(function (b) { b.addEventListener("click", function () {
      var v = b.getAttribute("data-ncat"); st.cat = (st.cat === v || v === "") ? "" : v; page = limit;
      $$("[data-ncat]").forEach(function (x) { var xv = x.getAttribute("data-ncat"); x.setAttribute("aria-pressed", String(xv === st.cat)); }); render(); }); });
    var rb = $("#rumor-only"); if (rb) rb.addEventListener("click", function () { st.rumor = !st.rumor; rb.setAttribute("aria-pressed", String(st.rumor)); page = limit; render(); });
    if (qBox2) qBox2.addEventListener("input", function () { st.q = qBox2.value.trim().toLowerCase(); page = limit; render(); });
    if (more) more.addEventListener("click", function () { page += limit; render(); });
    var hh = (location.hash || "").replace("#", ""); if (hh && CATS[hh]) { var bb = $('[data-ncat="' + hh + '"]'); if (bb) bb.click(); }
  }

  /* ---------- email signup (renders only if EMAIL_SIGNUP_URL is set) ---------- */
  $$("[data-signup]").forEach(function (box) {
    if (!EMAIL_SIGNUP_URL) { box.hidden = true; return; }
    box.hidden = false; var f = $("form", box); if (f) f.setAttribute("action", EMAIL_SIGNUP_URL);
  });

  /* ---------- sponsor slot (sponsors.json: [] by default, nothing shows) ---------- */
  var slot = $("[data-sponsor-slot]");
  if (slot) fetch("sponsors.json", { cache: "no-cache" }).then(function (r) { return r.json(); }).then(function (list) {
    if (!list || !list.length) return; var s = list[0];
    slot.innerHTML = '<span class="small">Sponsored</span><br><a href="' + esc(s.url) + '" rel="sponsored noopener" target="_blank"><b>' + esc(s.name) + '</b></a> ' + esc(s.blurb || "");
    slot.hidden = false; }).catch(function () {});
})();
