# LeakDeck

Tech launches, rumors and news, rated. A static site (plain HTML/CSS/JS, no framework, no build step to host) that runs itself:

- **Launch calendar** (`launches.json`): dates for phones, chips, laptops, games, gadgets and software, each marked Confirmed / Expected / Estimated / Released, with sources.
- **Rumor tracker** (`rumors.json`): every rumor rated **Confirmed / Likely / Rumor / Shaky** (or Debunked), with claim, reasoning, sources, last-updated date, and a "Resolved" track record.
- **News feed** (`news.json`): headline, source, link and time pulled from public RSS feeds (`feeds.json`). We never store or republish article text. The optional one-line summary comes only from `summaries.json` (our own wording, keyed by story URL).

## How it updates

`.github/workflows/update.yml` runs twice a day (and on demand):

1. `scripts/check_data.py` validates `launches.json` and `rumors.json`.
2. `scripts/update_news.py` fetches the feeds into `news.json` (stdlib only, no keys). One broken feed never breaks the run.
3. `scripts/build_pages.py` regenerates every HTML page, the per-launch and per-rumor pages, `sitemap.xml`, `robots.txt` and `feed.xml`.
4. The workflow commits any changes. Cloudflare Pages redeploys on every push.

## Editing (the editorial part)

- Add or change launches/rumors in the JSON files, run `python scripts/check_data.py && python scripts/build_pages.py`, commit and push.
- Every launch and rumor needs at least one https source. Mark uncertainty honestly: use `Estimated` for windows and `Rumor`/`Shaky` for weak claims. When something resolves, set the rumor's `status` to `Resolved`, add an `outcome`, and keep it as a track record.
- Add one-line summaries (your own words, never copied) to `summaries.json`: `{"<story url>": "summary"}`.
- Feeds: edit `feeds.json`. `default` tags a feed's stories with categories; `require_category` drops off-topic stories from general feeds. Junk filters live in `scripts/update_news.py` (`EXCLUDE`).

## Settings to fill in

| Where | What | Default |
|---|---|---|
| `scripts/build_pages.py` | `SITE_URL`, `CONTACT_EMAIL`, `SOCIAL` | `https://leakdeck.com` (planned, not yet registered) |
| `scripts/build_pages.py` | `CF_BEACON` (Cloudflare Web Analytics, token already set; emitted in every page `<head>`) | keep `CF_ANALYTICS_TOKEN` in `app.js` empty to avoid double counting |
| `app.js` | `EMAIL_SIGNUP_URL` (email provider form action) | empty = signup box hidden |
| `sponsors.json` | `[{"name":"...","url":"...","blurb":"..."}]` | `[]` = no sponsor shown |

After changing `SITE_URL`, run `python scripts/build_pages.py`.

## Themes

`themes.js` picks a seasonal accent from the date (Halloween, deal season, holiday, CES week, keynote season) and `themes.css` holds the colors. Preview with `?theme=halloween`, `?theme=ces`, ... or `?theme=none`. Dark/light: `?mode=dark|light`; the toggle remembers the choice.

## Preview locally

```
python3 -m http.server 8000
```

## Hosting

Cloudflare Pages, connected to this GitHub repo: framework preset **None**, build command empty, output directory `/`. Then add the custom domain.
