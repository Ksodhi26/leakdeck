#!/usr/bin/env python3
"""Fetch public RSS/Atom feeds into news.json.

What we keep per story: headline, link, source name, publish time, category tags, and a
rumor flag. We do NOT store or republish article text or feed descriptions. The optional
one-line "summary" comes only from summaries.json, which is written by hand/by the site
editor (original wording), keyed by story URL.

Standard library only, no API keys, no secrets. Safe to run daily from GitHub Actions:
    python scripts/update_news.py
"""
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; LeakDeckBot/1.0; +https://leakdeck.com/about)"
NOW = dt.datetime.now(dt.timezone.utc)

# Keyword rules (matched against the headline, lowercase). Order does not matter.
RULES = {
    "apple": r"\b(apple|iphone|ipad|ipados|ios ?\d*|macos|mac(book)?s?|imac|airpods?|vision pro|apple watch|watchos|homepod|apple tv|siri|tim cook|ternus|wwdc|m[1-9] (pro|max|ultra|chip)|a\d\d (pro|chip)|visionos|airtag)\b",
    "android": r"\b(android|pixel|google|gemini nano|chromebook|chrome os|oneplus|xiaomi|oppo|vivo|realme|honor|nothing phone|motorola|moto |galaxy|samsung|snapdragon|tensor|wear os|one ui|fairphone|poco|redmi|huawei|pixel watch)\b",
    "samsung": r"\b(samsung|galaxy|one ui|exynos|bixby)\b",
    "ai": r"\b(ai|a\.i\.|openai|chatgpt|gpt-?\d*|claude|anthropic|gemini|copilot|llm|grok|xai|deepseek|mistral|perplexity|meta ai|llama|sora|midjourney|agentic|agents?|machine learning|nvidia blackwell|neural|siri ai|qwen)\b",
    "gaming": r"\b(game|games|gaming|playstation|ps[345]|ps5 pro|xbox|nintendo|switch 2|steam|valve|gta|rockstar|esports|fortnite|zelda|pokemon|pokémon|call of duty|battlefield|elden ring|rtx|geforce|radeon|handheld|steam deck|steam machine|twitch)\b",
    "chips": r"\b(chip|chips|cpu|gpu|processor|silicon|intel|amd|nvidia|qualcomm|snapdragon|mediatek|dimensity|tsmc|arm|ryzen|core ultra|nova lake|zen ?\d|rtx|geforce|radeon|laptop|laptops|pc|pcs|motherboard|ssd|dram|ddr\d|hbm|memory|semiconductor|2nm|3nm|benchmark|geekbench|copilot\+|windows)\b",
    "evs": r"\b(ev|evs|electric vehicle|electric car|tesla|cybertruck|cybercab|robotaxi|waymo|rivian|lucid|byd|polestar|ioniq|supercharger|charging network|fsd|autopilot|optimus|zoox|nio|xpeng|e-bike|ebike|scooter|electric truck|f-150 lightning)\b",
}
RULES = {k: re.compile(v, re.I) for k, v in RULES.items()}
# Only show a story under "android" because of a brand word if it is not Samsung-only noise.
RUMOR = re.compile(
    r"\b(rumou?rs?|rumou?red|leaks?|leaked|leaker|leaking|reportedly|tipped|tipster|"
    r"spotted|appears? (online|in)|allegedly|said to|could|may|might|expected to|"
    r"set to launch|in the works|planning|surfaces?|reveals? (specs|design)|"
    r"benchmark(ed|s)? (listing|leak)|certification|certified|images? (show|leak)|renders?)\b",
    re.I,
)
# Words that make a headline clearly not rumor-ish even if it contains "could".
NOT_RUMOR = re.compile(r"\b(review|hands-on|best|deal|deals|how to|guide|vs\.?|tips)\b", re.I)


# Stories that are not tech news (puzzle answers, TV streams, coupon posts...). Add patterns as needed.
EXCLUDE = re.compile(
    r"(hints? and answers?|quordle|wordle|nyt (connections|strands)|connections hints|strands hints|"
    r"how to watch|free streams?|live ?stream(ing)? (of|for)|watch .{0,40} (live|free)|\bvs\.? .{0,40}(live|stream)|"
    r"coupon|promo code|best .{0,40} deals?|deals? of the (day|week)|early .{0,15} deals|prime day|horoscope|nfl|nba|nhl|mlb|premier league)",
    re.I,
)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    last = None
    for _ in range(2):  # one retry; some feeds are slow or big
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as e:
            last = e
    raise last


def strip_ns(tag):
    return tag.split("}", 1)[-1]


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        pass
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return None


def parse_feed(raw):
    """Return list of (title, link, datetime) from RSS 2.0 or Atom."""
    root = ET.fromstring(raw)
    out = []
    for el in root.iter():
        t = strip_ns(el.tag)
        if t not in ("item", "entry"):
            continue
        title = link = pub = None
        for ch in el:
            ct = strip_ns(ch.tag)
            if ct == "title":
                title = "".join(ch.itertext()).strip()
            elif ct == "link":
                link = (ch.get("href") or (ch.text or "")).strip() if (ch.get("href") or ch.text) else link
                if ch.get("rel") not in (None, "alternate") and link and ch.get("href"):
                    pass
            elif ct in ("pubDate", "published", "updated", "date") and not pub:
                pub = parse_date(ch.text)
        if title and link:
            out.append((html.unescape(re.sub(r"\s+", " ", title)).strip(), link, pub))
    return out


def clean_url(u):
    u = re.sub(r"[?&](utm_[a-z]+|ref|cmpid|taid|fbclid)=[^&]*", "", u)
    return u.rstrip("?&")


def categorize(title, defaults):
    cats = set(defaults)
    for k, rx in RULES.items():
        if rx.search(title):
            cats.add(k)
    # a Samsung-brand story is also Android; keep "samsung" visible on its own
    if "samsung" in cats:
        cats.add("android")
    return sorted(cats)


def is_rumor(title):
    return bool(RUMOR.search(title)) and not NOT_RUMOR.search(title)


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def pull(feed):
    try:
        items = parse_feed(fetch(feed["url"]))
        return feed, items[: feed.get("_max", 30)], None
    except Exception as e:  # one bad feed must never break the run
        return feed, [], f"{type(e).__name__}: {e}"


def main():
    cfg = load_json(ROOT / "feeds.json", {})
    feeds = cfg.get("feeds", [])
    max_age = dt.timedelta(days=cfg.get("max_age_days", 10))
    max_items = cfg.get("max_items", 600)
    for f in feeds:
        f["_max"] = cfg.get("per_feed_max", 30)

    old = load_json(ROOT / "news.json", {"items": []})
    store = {i["id"]: i for i in old.get("items", [])}
    summaries = load_json(ROOT / "summaries.json", {})

    ok, bad = 0, []
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(pull, feeds))
    for feed, items, err in results:
        if err:
            bad.append((feed["name"], err))
            continue
        ok += 1
        for title, link, pub in items:
            if EXCLUDE.search(title):
                continue
            if feed.get("require_category") and not categorize(title, feed.get("default", [])):
                continue  # general-news feeds: only keep stories that match a tech category
            link = clean_url(link)
            iid = hashlib.sha1(link.encode()).hexdigest()[:12]
            if iid in store:
                continue  # keep first-seen data stable
            pub = pub or NOW
            if pub > NOW + dt.timedelta(hours=2):
                pub = NOW
            store[iid] = {
                "id": iid,
                "title": title,
                "url": link,
                "source": feed["name"],
                "published": pub.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "categories": categorize(title, feed.get("default", [])),
                "rumor": is_rumor(title),
            }

    # Drop old stories, then the oldest beyond max_items
    keep = []
    for i in store.values():
        pub = parse_date(i["published"]) or NOW
        if NOW - pub <= max_age:
            keep.append(i)
    # Recompute tags every run so rule improvements apply to stored items
    feed_defaults = {f["name"]: f.get("default", []) for f in feeds}
    require = {f["name"] for f in feeds if f.get("require_category")}
    keep = [i for i in keep if not (i["source"] in require and not categorize(i["title"], feed_defaults.get(i["source"], [])))]
    for i in keep:
        i["categories"] = categorize(i["title"], feed_defaults.get(i["source"], []))
        i["rumor"] = is_rumor(i["title"])
        s = summaries.get(i["url"])
        if s:
            i["summary"] = s.strip()
        else:
            i.pop("summary", None)
    keep = [i for i in keep if not EXCLUDE.search(i["title"])]
    keep.sort(key=lambda i: i["published"], reverse=True)
    keep = keep[:max_items]

    if ok == 0 and old.get("items"):
        print("All feeds failed; leaving news.json untouched.", file=sys.stderr)
        for n, e in bad:
            print(f"  {n}: {e}", file=sys.stderr)
        return 0

    out = {
        "updated": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": sorted({i["source"] for i in keep}),
        "count": len(keep),
        "items": keep,
    }
    (ROOT / "news.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"feeds ok: {ok}/{len(feeds)}  stories kept: {len(keep)}")
    for n, e in bad:
        print(f"  feed failed: {n}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
