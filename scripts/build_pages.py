#!/usr/bin/env python3
"""Build all HTML pages, detail pages and sitemap from the JSON data files.

The output is plain static HTML that is committed to the repo, so hosting needs no build step.
Run after editing launches.json / rumors.json / news.json:
    python scripts/build_pages.py
Standard library only.
"""
import datetime as dt
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---- site settings (change here once the domain is bought) -------------------------------
SITE_NAME = "LeakDeck"
SITE_URL = "https://leakdeck.com"        # planned domain; no trailing slash
TAGLINE = "Tech launches, rumors and news, rated."
CONTACT_EMAIL = "hello@leakdeck.com"      # set up free forwarding with Cloudflare Email Routing
SOCIAL = {"x": "", "instagram": ""}  # fill in when the accounts exist
CATS = [("apple", "Apple"), ("android", "Google / Android"), ("samsung", "Samsung"),
        ("ai", "AI"), ("gaming", "Gaming"), ("chips", "Chips & PCs"), ("evs", "EVs")]
CATN = dict(CATS)
RATING_ORDER = ["Confirmed", "Likely", "Rumor", "Shaky", "Debunked"]
RATING_LEVEL = {"Confirmed": 4, "Likely": 3, "Rumor": 2, "Shaky": 1, "Debunked": 0}
# -------------------------------------------------------------------------------------------

TODAY = dt.datetime.now(dt.timezone.utc).date()
e = html.escape


def load(name, default):
    try:
        return json.loads((ROOT / name).read_text())
    except Exception:
        return default


LAUNCHES = load("launches.json", {"items": []})["items"]
RUMORS_DATA = load("rumors.json", {"items": [], "scale": {}})
RUMORS = RUMORS_DATA["items"]
SCALE = RUMORS_DATA.get("scale", {})
NEWS = load("news.json", {"items": [], "updated": ""})


def fmt_date(s):
    if not s:
        return ""
    d = dt.date.fromisoformat(s)
    return d.strftime("%b %-d, %Y")


def meter(rating):
    lvl = RATING_LEVEL.get(rating, 0)
    return '<span class="meter" aria-hidden="true">' + "".join(f'<i class="{"on" if n < lvl else ""}"></i>' for n in range(4)) + "</span>"


def rating_chip(rating):
    return f'<span class="chip r-{rating.lower()}" title="{e(SCALE.get(rating, ""))}">{meter(rating)} {e(rating)}</span>'


def status_chip(status):
    return f'<span class="chip s-{status.lower()}">{e(status)}</span>'


def cat_pills(cats):
    return "".join(f'<span class="pill">{e(CATN.get(c, c))}</span>' for c in cats)


def src_links(sources):
    return '<span class="srcs">Sources: ' + " ".join(f'<a href="{e(s["url"])}" rel="noopener" target="_blank">{e(s["name"])}</a>' for s in sources) + "</span>"


# ---------------------------------------------------------------- page shell
def head(title, desc, path, extra="", og="og-image.png", noindex=False):
    url = f"{SITE_URL}{path}"
    t = title if title.startswith(SITE_NAME) else f"{title} | {SITE_NAME}"
    return f"""<!doctype html>
<html lang="en" data-mode="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(t)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
{'<meta name="robots" content="noindex">' if noindex else '<meta name="robots" content="index, follow, max-image-preview:large">'}
<meta name="theme-color" content="#0b0d14">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{e(t)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE_URL}/{og}">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/atom+xml" title="{SITE_NAME} news" href="/feed.xml">
<script src="/themes.js"></script>
<link rel="stylesheet" href="/style.css">
<link rel="stylesheet" href="/themes.css">
{extra}
</head>
"""


def header(active=""):
    def a(href, label, key):
        cur = ' aria-current="page"' if active == key else ""
        return f'<a href="{href}"{cur}>{label}</a>'
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap bar">
  <a class="brand" href="/" aria-label="{SITE_NAME} home"><img src="/favicon.svg" alt="" width="36" height="36"><span class="word">Leak<b>Deck</b></span></a>
  <nav class="nav" aria-label="Main">
    {a("/launches.html", "Launches", "launches")}{a("/rumors.html", "Rumors", "rumors")}{a("/news.html", "News", "news")}{a("/about.html", "About", "about")}
    <button class="icon-btn" id="mode-toggle" type="button" aria-label="Toggle light or dark mode">☀️</button>
  </nav>
</div></header>
<main id="main">
"""


def footer():
    soc = ""
    if SOCIAL.get("x"):
        soc += f'<li><a href="{e(SOCIAL["x"])}" rel="me noopener">X / Twitter</a></li>'
    if SOCIAL.get("instagram"):
        soc += f'<li><a href="{e(SOCIAL["instagram"])}" rel="me noopener">Instagram</a></li>'
    return f"""</main>
<footer class="site-footer"><div class="wrap foot">
  <div><strong style="color:var(--ink2)">{SITE_NAME}</strong><p style="margin:6px 0 0">{e(TAGLINE)} Headlines link to the original publishers. Ratings are our editorial opinion, not facts about the companies.</p></div>
  <div><h4>Explore</h4><ul><li><a href="/launches.html">Launch calendar</a></li><li><a href="/rumors.html">Rumor tracker</a></li><li><a href="/news.html">Latest news</a></li><li><a href="/feed.xml">Atom feed</a></li>{soc}</ul></div>
  <div><h4>About</h4><ul><li><a href="/about.html">About and how we rate</a></li><li><a href="/disclosure.html">Ad &amp; affiliate disclosure</a></li><li><a href="/privacy.html">Privacy</a></li><li><a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></li></ul></div>
</div></footer>
<script src="/app.js" defer></script>
</body>
</html>
"""


def write(path, content):
    p = ROOT / path.lstrip("/")
    if p.suffix != ".html" and p.suffix != ".xml":
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"


# ---------------------------------------------------------------- cards
def launch_url(i):
    return f"/launch/{i['id']}/"


def rumor_url(r):
    return f"/rumor/{r['id']}/"


def launch_card(i, compact=False):
    sd = i["date"] if i.get("precision") == "day" and i["status"] != "Released" else ""
    count = f'<span class="count" data-count="{sd}"></span>' if sd else ""
    text = " ".join([i["name"], i["brand"], i["type"], i["summary"], " ".join(CATN.get(c, c) for c in i["categories"])]).lower()
    cats_shown = [c for c in i["categories"] if CATN.get(c) != i["brand"]]
    meta = f'<span class="pill">{e(i["brand"])}</span><span class="pill">{e(i["type"])}</span>'
    if i.get("price"):
        meta += f'<span class="pill">{e(i["price"])}</span>'
    acts = ""
    if not compact:
        if i.get("precision") == "day" and i["status"] != "Released":
            acts += f'<button class="btn ghost sm" type="button" data-ics="{i["date"]}" data-name="{e(i["name"])}" data-url="{SITE_URL}{launch_url(i)}">+ Add to calendar</button>'
        acts += f'<a class="btn ghost sm" href="{launch_url(i)}">Details</a>'
    return f"""<article class="card launch" id="{i['id']}" data-cats="{' '.join(i['categories'])}" data-status="{e(i['status'])}" data-date="{i['date']}" data-text="{e(text)}">
  <div class="card-top">{status_chip(i['status'])}<span class="when">{e(i['date_label'])}</span>{count}</div>
  <h3><a href="{launch_url(i)}">{e(i['name'])}</a></h3>
  <p>{e(i['summary'])}</p>
  <div class="meta">{meta}{cat_pills(cats_shown)}</div>
  {src_links(i['sources'][:3]) if not compact else ''}
  {'<div class="card-actions">'+acts+'</div>' if acts else ''}
</article>"""


def rumor_card(r, compact=False):
    text = " ".join([r["title"], r["claim"], r["why"], " ".join(CATN.get(c, c) for c in r["categories"])]).lower()
    exp = f'<span class="pill">Expected: {e(r["expected"])}</span>' if r.get("expected") else ""
    outcome = f'<p class="why"><strong>Outcome:</strong> {e(r["outcome"])}</p>' if r.get("outcome") else ""
    body = "" if compact else f'<p class="claim">Claim: {e(r["claim"])}</p><p class="why">{e(r["why"])}</p>{outcome}{src_links(r["sources"])}'
    return f"""<article class="card rumor-card" id="{r['id']}" data-cats="{' '.join(r['categories'])}" data-rating="{e(r['rating'])}" data-status="{e(r['status'])}" data-text="{e(text)}">
  <div class="card-top">{rating_chip(r['rating'])}<span class="when">Updated {fmt_date(r['updated'])}</span></div>
  <h3><a href="{rumor_url(r)}">{e(r['title'])}</a></h3>
  {body}
  <div class="meta">{exp}{cat_pills(r['categories'])}</div>
</article>"""


def chips(attr, with_all=False, label_all="All"):
    out = "".join(f'<button class="tag" type="button" {attr}="{k}" aria-pressed="false">{e(v)}</button>' for k, v in CATS)
    return out


def news_item_html(i):
    s = f'<span class="sum">{e(i["summary"])}</span>' if i.get("summary") else ""
    return (f'<li><a class="t" href="{e(i["url"])}" rel="noopener nofollow" target="_blank">{e(i["title"])}</a>{s}'
            f'<span class="m"><span class="src">{e(i["source"])}</span>' + (' <span class="badge-rumor">Rumor mill</span>' if i.get("rumor") else "") + "</span></li>")


# ---------------------------------------------------------------- derive sets
def upcoming():
    out = [i for i in LAUNCHES if i["status"] != "Released"]
    out.sort(key=lambda i: (i.get("sort_date") or i["date"]))
    return out


def released():
    out = [i for i in LAUNCHES if i["status"] == "Released"]
    out.sort(key=lambda i: i["date"], reverse=True)
    return out


def month_label(d):
    return dt.date.fromisoformat(d).strftime("%B %Y")


# ---------------------------------------------------------------- pages
def build_index():
    up = [i for i in upcoming() if i["status"] in ("Confirmed", "Expected") and i["precision"] == "day"][:6]
    ru = [r for r in RUMORS if r["status"] == "Active"]
    ru.sort(key=lambda r: (-RATING_LEVEL[r["rating"]], r["updated"]))
    pick = []  # a mix of ratings: 2 Likely, 2 Rumor, 1 Shaky, plus the freshest Confirmed track-record entry
    for rating, n in (("Likely", 2), ("Rumor", 2), ("Shaky", 2)):
        pick += [r for r in ru if r["rating"] == rating][:n]
    ru = pick
    news = NEWS["items"][:10]
    n_up = len([i for i in LAUNCHES if i["status"] != "Released"])
    n_ru = len([r for r in RUMORS if r["status"] == "Active"])
    ld = jsonld({"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/", "description": TAGLINE,
         "potentialAction": {"@type": "SearchAction", "target": f"{SITE_URL}/news.html?q={{search_term_string}}", "query-input": "required name=search_term_string"}},
        {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/", "logo": f"{SITE_URL}/icon-512.png",
         "sameAs": [v for v in SOCIAL.values() if v]}]})
    h = head("LeakDeck: Tech launch calendar, rumor tracker and news", "Upcoming phones, chips, laptops, games and gadgets with dates, plus a rumor tracker that rates how credible each leak is. Daily tech headlines from top sources.", "/", ld)
    body = f"""<section class="hero"><div class="wrap">
  <p class="theme-tagline"></p>
  <span class="eyebrow">Updated daily</span>
  <h1>Tech launches, rumors and news, <span class="hl">rated.</span></h1>
  <p class="lead">A launch calendar with real dates, a rumor tracker that tells you how much to believe each leak, and the day's headlines from the sites you already read.</p>
  <form class="search" action="/news.html" method="get" role="search"><input type="search" name="q" placeholder="Search headlines: iPhone, RTX, Galaxy S27..." aria-label="Search headlines"><button class="btn" type="submit">Search</button></form>
  <div class="stats"><span class="stat"><b>{n_up}</b>launches tracked</span><span class="stat"><b>{n_ru}</b>active rumors rated</span><span class="stat"><b>{len(NEWS['items'])}</b>recent headlines</span></div>
</div></section>
<section class="block"><div class="wrap">
  <div class="sec-head"><h2>Next up</h2><a href="/launches.html">Full launch calendar &rarr;</a></div>
  <div class="grid">{''.join(launch_card(i, compact=True) for i in up)}</div>
</div></section>
<section class="block"><div class="wrap">
  <div class="sec-head"><h2>Rumor board</h2><a href="/rumors.html">All rumors &rarr;</a></div>
  <div class="grid">{''.join(rumor_card(r, compact=True) for r in ru)}</div>
  <p class="small" style="margin-top:10px">Ratings: Confirmed, Likely, Rumor, Shaky. <a href="/about.html#ratings">How we rate</a>.</p>
</div></section>
<section class="block"><div class="wrap">
  <div class="sec-head"><h2>Latest headlines</h2><a href="/news.html">All news &rarr;</a></div>
  <div class="filters"><button class="tag" type="button" data-ncat="" aria-pressed="true">All</button>{chips('data-ncat')}</div>
  <ul class="news" id="news-list" data-limit="10">{''.join(news_item_html(i) for i in news)}</ul>
  <p class="small" id="news-status" style="margin-top:8px"></p>
</div></section>
<section class="block"><div class="wrap">
  <div class="cols3">
    <div class="callout"><h3>Launch calendar</h3><p>Dates for phones, chips, laptops, games and software, marked Confirmed, Expected or Estimated.</p><a class="btn sm" href="/launches.html">Open calendar</a></div>
    <div class="callout"><h3>Rumor tracker</h3><p>Every rumor gets a credibility rating, its sources and a last-updated date, and we keep score when they resolve.</p><a class="btn sm" href="/rumors.html">See ratings</a></div>
    <div class="callout" data-signup hidden><h3>Weekly digest</h3><p>The week's launches and rumor changes, in your inbox.</p><form class="signup" method="post"><input type="email" name="email" placeholder="you@example.com" required aria-label="Email address"><button class="btn sm" type="submit">Subscribe</button></form></div>
  </div>
  <div class="sponsor-slot" data-sponsor-slot hidden style="margin-top:16px"></div>
</div></section>
"""
    write("/index.html", h + header("") + body + footer())


def build_launches():
    ld = jsonld({"@context": "https://schema.org", "@type": "ItemList", "name": "Upcoming tech launches",
                 "itemListElement": [{"@type": "ListItem", "position": n + 1, "url": SITE_URL + launch_url(i), "name": i["name"]} for n, i in enumerate(upcoming())]})
    h = head("Tech launch calendar: upcoming phones, chips, laptops and games", "Dates for upcoming phones, chips, laptops, games, gadgets and software, marked Confirmed, Expected or Estimated, with sources.", "/launches.html", ld)
    parts, last = [], None
    for i in upcoming():
        m = month_label(i.get("sort_date") or i["date"])
        if m != last:
            parts.append(f'<h2 class="month">{m}</h2>')
            last = m
        parts.append(launch_card(i))
    rel = "".join(launch_card(i) for i in released())
    body = f"""<div class="wrap prose"><h1>Tech launch calendar</h1>
<p>What is coming, when, and how sure we are. <strong>Confirmed</strong> means the company or organizer has said so. <strong>Expected</strong> is a credible report of a specific date. <strong>Estimated</strong> is a window based on patterns or reports. Last updated {fmt_date(str(TODAY))}.</p></div>
<div class="wrap">
<div class="filters"><input class="grow" id="filter-q" type="search" placeholder="Search launches..." aria-label="Search launches">
 <button class="tag" type="button" data-f="confirmed" aria-pressed="false">Confirmed</button><button class="tag" type="button" data-f="expected" aria-pressed="false">Expected / Estimated</button><button class="tag" type="button" data-f="released" aria-pressed="false">Recently released</button></div>
<div class="filters">{chips('data-cat')}</div>
<div id="launch-list">
{_launch_groups(parts)}
<h2 class="month">Recently released</h2>
<div class="grid two">{rel}</div>
</div>
<p class="empty" id="empty" hidden>No launches match those filters.</p>
</div>
"""
    write("/launches.html", h + header("launches") + body + footer())


def _launch_groups(parts):
    """Wrap each month heading's cards in a grid so the filter script can find siblings."""
    out, buf = [], []
    for p in parts:
        if p.startswith('<h2 class="month">'):
            if buf:
                out.append('<div class="grid two">' + "".join(buf) + "</div>")
                buf = []
            out.append(p)
        else:
            buf.append(p)
    if buf:
        out.append('<div class="grid two">' + "".join(buf) + "</div>")
    return "\n".join(out)


def build_rumors():
    active = sorted([r for r in RUMORS if r["status"] == "Active"], key=lambda r: (-RATING_LEVEL[r["rating"]], r["updated"]), reverse=False)
    active.sort(key=lambda r: (-RATING_LEVEL[r["rating"]], -int(r["updated"].replace("-", ""))))
    resolved = [r for r in RUMORS if r["status"] != "Active"]
    legend = "".join(f'<div>{rating_chip(k)}<br>{e(v)}</div>' for k, v in SCALE.items())
    ld = jsonld({"@context": "https://schema.org", "@type": "ItemList", "name": "Tech rumors with credibility ratings",
                 "itemListElement": [{"@type": "ListItem", "position": n + 1, "url": SITE_URL + rumor_url(r), "name": r["title"]} for n, r in enumerate(RUMORS)]})
    h = head("Tech rumor tracker: how credible is each leak?", "Every major tech rumor rated Confirmed, Likely, Rumor or Shaky, with sources, what would change the rating, and a track record of past calls.", "/rumors.html", ld)
    body = f"""<div class="wrap prose"><h1>Rumor tracker</h1>
<p>Leaks are not all equal. We rate each rumor by the quality of the evidence and keep the sources next to it. Ratings change as news comes in, and resolved rumors stay up as a track record.</p></div>
<div class="wrap"><div class="legend">{legend}</div>
<div class="filters" style="margin-top:16px"><input class="grow" id="filter-q" type="search" placeholder="Search rumors..." aria-label="Search rumors">
 {''.join(f'<button class="tag" type="button" data-f="{k.lower()}" aria-pressed="false">{k}</button>' for k in ["Confirmed", "Likely", "Rumor", "Shaky"])}<button class="tag" type="button" data-f="resolved" aria-pressed="false">Resolved</button></div>
<div class="filters">{chips('data-cat')}</div>
<div id="rumor-list"><h2 class="group month">Active rumors</h2><div class="grid two">{''.join(rumor_card(r) for r in active)}</div>
<h2 class="group month">Track record: resolved</h2><div class="grid two">{''.join(rumor_card(r) for r in resolved)}</div></div>
<p class="empty" id="empty" hidden>No rumors match those filters.</p></div>
"""
    write("/rumors.html", h + header("rumors") + body + footer())


def build_news():
    top = NEWS["items"][:40]
    h = head("Latest tech news headlines", "Today's headlines from The Verge, Ars Technica, Engadget, 9to5Mac, 9to5Google, MacRumors and more, filtered by Apple, Android, Samsung, AI, gaming, chips and EVs.", "/news.html")
    body = f"""<div class="wrap prose"><h1>Latest tech news</h1>
<p>Headlines from public RSS feeds, refreshed daily. We link to the original publisher for every story. "Rumor mill" flags headlines that sound like leaks or reports, which is a hint, not a rating.</p></div>
<div class="wrap">
<div class="filters"><input class="grow" id="filter-q" type="search" placeholder="Search headlines..." aria-label="Search headlines">
 <button class="tag" type="button" id="rumor-only" aria-pressed="false">Rumor mill only</button></div>
<div class="filters"><button class="tag" type="button" data-ncat="" aria-pressed="true">All</button>{chips('data-ncat')}</div>
<ul class="news" id="news-list" data-limit="40">{''.join(news_item_html(i) for i in top)}</ul>
<p style="margin-top:14px"><button class="btn ghost" type="button" id="news-more">Show more</button> <span class="small" id="news-status"></span></p>
<noscript><p class="small">Turn on JavaScript to filter and search all headlines.</p></noscript>
</div>
"""
    write("/news.html", h + header("news") + body + footer())


def build_about():
    legend = "".join(f'<div>{rating_chip(k)}<br>{e(v)}</div>' for k, v in SCALE.items())
    h = head("About LeakDeck and how we rate rumors", "What LeakDeck is, how the launch calendar and rumor ratings work, and how we handle corrections.", "/about.html")
    body = f"""<div class="wrap prose"><h1>About {SITE_NAME}</h1>
<p>{SITE_NAME} is a small, independent site for people who want to know what tech is coming, when, and whether the leaks are worth believing. It has three parts: a <a href="/launches.html">launch calendar</a>, a <a href="/rumors.html">rumor tracker</a> and a <a href="/news.html">daily headline feed</a>.</p>
<h2 id="ratings">How we rate rumors</h2>
<p>Each rumor gets one of four ratings, based on the evidence rather than on how exciting it is:</p></div>
<div class="wrap"><div class="legend">{legend}</div></div>
<div class="wrap prose">
<p>We look at who is reporting it (company, regulator, database, supply chain, a named reporter with a track record, or an anonymous tipster), whether independent sources agree, and how the source has done before. When a rumor resolves we mark it Confirmed, Debunked or Resolved and keep it on the page as a track record, including the details that turned out wrong.</p>
<h2>How the calendar works</h2>
<p><strong>Confirmed</strong> dates come from the company or event organizer. <strong>Expected</strong> is a credible report of a specific date. <strong>Estimated</strong> is a window based on past patterns or reports. Every entry lists its sources. Dates change, so check the source before you plan around one.</p>
<h2>How the news feed works</h2>
<p>We read public RSS feeds from publishers such as The Verge, Ars Technica, Engadget, 9to5Mac, 9to5Google, MacRumors and Android Authority. We show only the headline, source and time, plus a short summary in our own words on some stories, and always link to the original. We do not copy or republish article text. If you are a publisher and want a feed removed, email us and we will remove it.</p>
<h2>Corrections and tips</h2>
<p>Spot a mistake, or have a source we should add? Email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>. We fix errors quickly and note material corrections on the page.</p>
<h2>Independence</h2>
<p>Ratings are editorial and cannot be bought. If we ever add affiliate links or sponsors, they will be labeled and will not change a rating. See the <a href="/disclosure.html">disclosure page</a>.</p></div>
"""
    write("/about.html", h + header("about") + body + footer())


def build_privacy():
    h = head("Privacy policy", "How LeakDeck handles data: no accounts, no tracking cookies of our own, and what changes if we add analytics, email signup or ads.", "/privacy.html")
    body = f"""<div class="wrap prose"><h1>Privacy policy</h1><p class="small">Last updated {fmt_date(str(TODAY))}</p>
<p>The short version: {SITE_NAME} has no accounts and does not sell personal data.</p>
<h2>What we collect</h2>
<ul><li><strong>Nothing you type</strong> unless you use the email signup (when it is switched on) or email us.</li>
<li><strong>Your display preference.</strong> If you toggle light/dark mode, your browser stores that choice locally (localStorage). It never leaves your device.</li>
<li><strong>Basic traffic stats.</strong> When enabled, we use Cloudflare Web Analytics, which does not use cookies or track you across sites. Our host (Cloudflare) also keeps standard server logs, such as IP address and page requested, for security and reliability.</li></ul>
<h2>Email signup</h2><p>If we offer a newsletter, your address is stored by our email provider and used only to send the digest. Every email has an unsubscribe link.</p>
<h2>Ads and affiliate links</h2><p>We may show ads or use affiliate links in the future. Ad networks and retailers can set their own cookies under their own policies, and if we add them we will update this page and show a consent choice where the law requires it. See the <a href="/disclosure.html">disclosure page</a>.</p>
<h2>Links to other sites</h2><p>We link to news publishers and company sites. They have their own privacy practices.</p>
<h2>Your rights</h2><p>Depending on where you live (for example California or the EU/UK), you may have the right to access, correct or delete personal data we hold. Email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> and we will respond. {SITE_NAME} is not directed at children under 13.</p>
<h2>Changes</h2><p>We will post changes here and update the date above.</p></div>
"""
    write("/privacy.html", h + header("") + body + footer())


def build_disclosure():
    h = head("Ad and affiliate disclosure", "How LeakDeck is funded, how we label affiliate links and sponsors, and why they never affect our ratings.", "/disclosure.html")
    body = f"""<div class="wrap prose"><h1>Ad and affiliate disclosure</h1><p class="small">Last updated {fmt_date(str(TODAY))}</p>
<p>{SITE_NAME} is free to read. We plan to cover costs through ads, affiliate links and clearly labeled sponsorships. This page explains how that works so you can judge our coverage.</p>
<h2>Current status</h2><p>As of the date above, this site shows no ads and has no affiliate or sponsor relationships.</p>
<h2>Affiliate links</h2><p>If we add links to retailers or manufacturers and you buy something through them, we may earn a commission at no extra cost to you. Links like that will be marked (for example "affiliate link") next to the link. When we join a program that requires specific wording, such as Amazon Associates, we will include it: "As an Amazon Associate we earn from qualifying purchases."</p>
<h2>Ads</h2><p>If we show advertising, it will be labeled and kept separate from our editorial content. Ad networks may use cookies; see our <a href="/privacy.html">privacy policy</a>.</p>
<h2>Sponsors</h2><p>Sponsored placements will be labeled "Sponsored". Sponsors cannot review, change or buy a rumor rating, a launch date or a news item.</p>
<h2>Editorial independence</h2><p>Ratings come from our reading of the evidence. Money does not change them. If a conflict of interest exists on a specific story we will say so.</p>
<h2>Questions</h2><p>Email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>.</p></div>
"""
    write("/disclosure.html", h + header("") + body + footer())


def build_404():
    h = head("Page not found", "That page does not exist.", "/404.html", noindex=True)
    body = '<div class="wrap prose"><h1>Page not found</h1><p>That link may be old. Try the <a href="/launches.html">launch calendar</a>, the <a href="/rumors.html">rumor tracker</a> or the <a href="/news.html">latest news</a>.</p></div>'
    write("/404.html", h + header("") + body + footer())


def crumb(items):
    return '<nav class="crumbs" aria-label="Breadcrumb"><div class="wrap">' + " / ".join(f'<a href="{u}">{e(t)}</a>' for t, u in items) + "</div></nav>"


def build_launch_details():
    shutil.rmtree(ROOT / "launch", ignore_errors=True)
    for i in LAUNCHES:
        path = launch_url(i)
        ld = {"@context": "https://schema.org", "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Launch calendar", "item": SITE_URL + "/launches.html"},
                {"@type": "ListItem", "position": 2, "name": i["name"], "item": SITE_URL + path}]}]}
        if i["type"] == "Event" and i["precision"] == "day":
            ld["@graph"].append({"@type": "Event", "name": i["name"], "startDate": i["date"], "description": i["summary"],
                                 "eventStatus": "https://schema.org/EventScheduled", "url": SITE_URL + path})
        h = head(f"{i['name']}: release date and details", i["summary"], path, jsonld(ld))
        rows = [("Status", status_chip(i["status"])), ("Date", e(i["date_label"])), ("Maker", e(i["brand"])), ("Type", e(i["type"]))]
        if i.get("price"):
            rows.append(("Price", e(i["price"])))
        rows.append(("Categories", cat_pills(i["categories"])))
        facts = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows)
        srcs = "".join(f'<li><a href="{e(s["url"])}" rel="noopener" target="_blank">{e(s["name"])}</a></li>' for s in i["sources"])
        rel = [r for r in RUMORS if set(r["categories"]) & set(i["categories"]) and r["status"] == "Active"][:3]
        relhtml = ""
        if rel:
            relhtml = '<h2>Related rumors</h2><div class="grid">' + "".join(rumor_card(r, compact=True) for r in rel) + "</div>"
        ics = ""
        if i["precision"] == "day" and i["status"] != "Released":
            ics = f'<p><button class="btn sm" type="button" data-ics="{i["date"]}" data-name="{e(i["name"])}" data-url="{SITE_URL}{path}">+ Add to calendar</button></p>'
        body = crumb([("Launch calendar", "/launches.html"), (i["name"], path)]) + f"""<div class="wrap prose"><h1>{e(i['name'])}</h1>
<p><strong>{e(i['summary'])}</strong></p><p>{e(i['details'])}</p>{ics}
<dl class="facts">{facts}</dl><h2>Sources</h2><ul>{srcs}</ul>
<p class="small">Launch dates can change. Check the sources for the latest. Last reviewed {fmt_date(load('launches.json', {}).get('updated', str(TODAY)))}.</p></div>
<div class="wrap">{relhtml}</div>"""
        write(path, h + header("launches") + body + footer())


def build_rumor_details():
    shutil.rmtree(ROOT / "rumor", ignore_errors=True)
    for r in RUMORS:
        path = rumor_url(r)
        ld = {"@context": "https://schema.org", "@type": "ClaimReview", "url": SITE_URL + path,
              "claimReviewed": r["claim"], "datePublished": r["updated"],
              "author": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL},
              "reviewRating": {"@type": "Rating", "ratingValue": max(1, RATING_LEVEL[r["rating"]]), "bestRating": 4, "worstRating": 1, "alternateName": r["rating"]}}
        h = head(f"{r['title']}: {r['rating']}", f"{r['rating']}: {r['claim']}", path, jsonld(ld))
        rows = [("Rating", rating_chip(r["rating"])), ("Status", e(r["status"]))]
        if r.get("expected"):
            rows.append(("Expected", e(r["expected"])))
        if r.get("first_reported"):
            rows.append(("First reported", fmt_date(r["first_reported"])))
        rows.append(("Last updated", fmt_date(r["updated"])))
        rows.append(("Categories", cat_pills(r["categories"])))
        facts = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows)
        srcs = "".join(f'<li><a href="{e(s["url"])}" rel="noopener" target="_blank">{e(s["name"])}</a></li>' for s in r["sources"])
        outcome = f'<h2>Outcome</h2><p>{e(r["outcome"])}</p>' if r.get("outcome") else ""
        body = crumb([("Rumor tracker", "/rumors.html"), (r["title"], path)]) + f"""<div class="wrap prose"><h1>{e(r['title'])}</h1>
<dl class="facts">{facts}</dl><h2>The claim</h2><p>{e(r['claim'])}</p><h2>Why we rated it {e(r['rating'])}</h2><p>{e(r['why'])}</p>{outcome}
<h2>Sources</h2><ul>{srcs}</ul><p class="small">Ratings are editorial opinion and change as evidence changes. <a href="/about.html#ratings">How we rate</a>.</p></div>"""
        write(path, h + header("rumors") + body + footer())


def build_feed():
    """Atom feed of rumor and launch updates (not news headlines, which belong to their publishers)."""
    entries = []
    for r in sorted(RUMORS, key=lambda r: r["updated"], reverse=True)[:30]:
        entries.append(f"""<entry><title>{e(r['rating'])}: {e(r['title'])}</title><link href="{SITE_URL}{rumor_url(r)}"/><id>{SITE_URL}{rumor_url(r)}</id><updated>{r['updated']}T12:00:00Z</updated><summary>{e(r['claim'])}</summary></entry>""")
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>{SITE_NAME}: rumor ratings</title><link href="{SITE_URL}/rumors.html"/><link rel="self" href="{SITE_URL}/feed.xml"/><id>{SITE_URL}/</id><updated>{TODAY}T12:00:00Z</updated>{''.join(entries)}</feed>
"""
    (ROOT / "feed.xml").write_text(xml)


def build_sitemap():
    today = str(TODAY)
    urls = [("/", "daily", "1.0"), ("/launches.html", "daily", "0.9"), ("/rumors.html", "daily", "0.9"), ("/news.html", "daily", "0.8"),
            ("/about.html", "monthly", "0.4"), ("/disclosure.html", "yearly", "0.2"), ("/privacy.html", "yearly", "0.2")]
    urls += [(launch_url(i), "weekly", "0.6") for i in LAUNCHES]
    urls += [(rumor_url(r), "weekly", "0.6") for r in RUMORS]
    rows = "".join(f"<url><loc>{SITE_URL}{u}</loc><lastmod>{today}</lastmod><changefreq>{f}</changefreq><priority>{p}</priority></url>" for u, f, p in urls)
    (ROOT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>\n')
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")


def main():
    build_index(); build_launches(); build_rumors(); build_news(); build_about(); build_privacy(); build_disclosure(); build_404()
    build_launch_details(); build_rumor_details(); build_feed(); build_sitemap()
    print(f"built: {len(LAUNCHES)} launches, {len(RUMORS)} rumors, {len(NEWS['items'])} headlines")


if __name__ == "__main__":
    main()
