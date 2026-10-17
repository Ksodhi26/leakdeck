/* LeakDeck themes: sets <html data-theme="..."> from today's date (America/Los_Angeles) and the
   tagline text. Loaded in <head> without defer so colors are right on first paint.
   Preview: ?theme=halloween | dealseason | holiday | ces | keynote | none  */
(function () {
  "use strict";
  var root = document.documentElement;
  var THEMES = {
    halloween: { tagline: "Spooky season: the scariest leaks 🎃" },
    dealseason: { tagline: "Deal season: what's worth buying 🛒" },
    holiday: { tagline: "Holiday gadget watch 🎁" },
    ces: { tagline: "CES season: everything new in Vegas ⚡" },
    keynote: { tagline: "Keynote season: Apple, Google and Samsung events 📅" }
  };
  function today() {
    try {
      var o = {};
      new Intl.DateTimeFormat("en-US", { timeZone: "America/Los_Angeles", year: "numeric", month: "numeric", day: "numeric" })
        .formatToParts(new Date()).forEach(function (p) { o[p.type] = parseInt(p.value, 10); });
      if (o.month && o.day) return o;
    } catch (e) {}
    var n = new Date(); return { year: n.getFullYear(), month: n.getMonth() + 1, day: n.getDate() };
  }
  function pick(t) {
    var md = t.month * 100 + t.day;
    if (md >= 1001 && md <= 1101) return "halloween";   // Oct 1 - Nov 1
    if (md >= 1120 && md <= 1202) return "dealseason";  // Black Friday / Cyber Monday run-up
    if (md >= 1203 && md <= 1231) return "holiday";     // December
    if (md >= 101 && md <= 112) return "ces";           // CES week (early Jan)
    if (md >= 901 && md <= 915) return "keynote";       // iPhone event season
    return "";
  }
  var q = (location.search.match(/[?&]theme=([a-z]+)/) || [])[1];
  var name = q ? (q === "none" ? "" : q) : pick(today());
  if (name && THEMES[name]) {
    root.setAttribute("data-theme", name);
    root.style.setProperty("--theme-tagline", JSON.stringify(THEMES[name].tagline));
    document.addEventListener("DOMContentLoaded", function () {
      document.querySelectorAll(".theme-tagline").forEach(function (el) { el.textContent = THEMES[name].tagline; });
    });
  }
  // dark / light mode (dark by default; respects the system setting until the user toggles)
  var saved = null; try { saved = localStorage.getItem("ld-mode"); } catch (e) {}
  var qm = (location.search.match(/[?&]mode=(dark|light)/) || [])[1];
  var mode = qm || saved || (window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  root.setAttribute("data-mode", mode);
})();
