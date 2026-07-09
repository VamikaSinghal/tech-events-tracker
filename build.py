#!/usr/bin/env python3
"""
Fetches tech / hackathon / startup events for your city and builds a web page
(index.html) that GitHub Pages will host for you.

You almost never need to edit this file.
To change your city or interests, edit  config.json  instead.
"""

import json
import re
import html
import datetime
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dateutil import parser as dateparser

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (event-tracker; personal use)"}

# Generic words that mark a Luma event as tech/startup-relevant. Luma's
# discover feed is a general local-events feed (book clubs, run clubs,
# concerts...), unlike Devpost which is hackathons-only, so Luma results are
# always narrowed by these plus your own config.json keywords — see
# filter_events().
GENERIC_TECH_KEYWORDS = [
    "tech", "startup", "founder", "founders", "venture", "vc", "hackathon",
    "engineer", "engineering", "developer", "product", "ai", "ml",
    "machine learning", "artificial intelligence", "web3", "crypto",
    "blockchain", "saas", "software", "coding", "hacker", "demo day",
    "pitch", "y combinator",
]

# A few common shorthands people type as "city" that don't match Luma's
# official place names.
LUMA_CITY_ALIASES = {
    "nyc": "new york",
    "new york city": "new york",
    "sf": "san francisco",
    "bay area": "san francisco",
    "la": "los angeles",
    "dc": "washington, dc",
    "washington dc": "washington, dc",
    "bangalore": "bengaluru",
    "delhi": "new delhi",
    "bombay": "mumbai",
    "saigon": "ho chi minh city",
}


def fold_accents(text):
    """'São Paulo' -> 'sao paulo', so typed input without accents still
    matches Luma's place names."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower()


# ----------------------------------------------------------------------
# 1. Load your settings
# ----------------------------------------------------------------------
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# 2. Get events from Devpost (hackathons). No API key needed.
#    Devpost has a public JSON endpoint we can politely query.
# ----------------------------------------------------------------------
def fetch_devpost(city, max_pages=6):
    events = []
    for page in range(1, max_pages + 1):
        url = "https://devpost.com/api/hackathons"
        # Ask Devpost only for events still open or upcoming, soonest first —
        # so we don't waste pages on hackathons that already ended.
        params = {
            "search": city,
            "page": page,
            "status[]": ["upcoming", "open"],
            "order_by": "deadline",
        }
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:  # network hiccup, bad page, etc.
            print(f"  ! skipped Devpost page {page}: {e}")
            continue

        batch = data.get("hackathons", [])
        if not batch:
            break

        for h in batch:
            loc = (h.get("displayed_location") or {}).get("location", "")
            themes = [t.get("name", "") for t in h.get("themes", [])]
            dates = h.get("submission_period_dates", "").strip()
            events.append(
                {
                    "source": "Devpost",
                    "title": h.get("title", "").strip(),
                    "url": h.get("url", ""),
                    "location": loc.strip(),
                    "dates": dates,
                    "sort_date": parse_devpost_date(dates),
                    "state": h.get("open_state", ""),  # upcoming / open / ended
                    "themes": themes,
                    "prize": strip_html(h.get("prize_amount", "")),
                    "organization": h.get("organization_name") or "",
                }
            )
    return events


def parse_devpost_date(text):
    """Devpost's date field is a display string like 'Oct 03 - 04, 2026', not
    ISO, and ranges can span months/years ('Dec 01, 2026 - Jan 05, 2027'). We
    only need the *start* date, so take the first segment and, if it's
    missing a year (the common same-month-range case), borrow the year from
    the second segment. Anything we can't confidently parse (e.g. 'Ongoing')
    returns None rather than guessing.
    """
    if not text:
        return None
    first_part, _, rest = text.strip().partition(" - ")
    if not re.search(r"\d{4}", first_part) and rest:
        year_match = re.search(r"\d{4}", rest)
        if year_match:
            first_part = f"{first_part}, {year_match.group()}"
    if not re.search(r"\d{4}", first_part):
        return None
    try:
        return dateparser.parse(first_part, default=datetime.datetime(2000, 1, 1))
    except (ValueError, OverflowError):
        return None


def strip_html(text):
    """Devpost wraps prize numbers in HTML tags — clean them up."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


# ----------------------------------------------------------------------
# 3. Get events from Luma (lu.ma) — general tech/startup meetups, mixers,
#    demo days. No API key needed: lu.ma/discover embeds a JSON blob in the
#    page HTML that lists every city it covers, and its pagination API is
#    open to the public (it's what the site's own frontend calls).
# ----------------------------------------------------------------------
def get_luma_places():
    try:
        resp = requests.get("https://lu.ma/discover", headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ! could not load Luma's city list: {e}")
        return []

    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.S
    )
    if not match:
        print("  ! Luma discover page format changed, skipping Luma")
        return []

    try:
        data = json.loads(match.group(1))
        raw_places = data["props"]["pageProps"]["initialData"]["places"]
    except Exception as e:
        print(f"  ! could not parse Luma's city list: {e}")
        return []

    places = []
    for entry in raw_places:
        place = entry.get("place") or {}
        if place.get("slug") and place.get("api_id"):
            places.append(
                {
                    "name": place.get("name", ""),
                    "slug": place["slug"],
                    "api_id": place["api_id"],
                }
            )
    return places


def match_luma_place(city, places):
    if not city or not places:
        return None
    needle = fold_accents(city.strip())
    needle = LUMA_CITY_ALIASES.get(needle, needle)
    needle_slug = re.sub(r"[^a-z0-9]+", "-", needle).strip("-")

    for p in places:
        if fold_accents(p["name"]) == needle:
            return p
    for p in places:
        if p["slug"] == needle_slug:
            return p
    for p in places:
        name_folded = fold_accents(p["name"])
        if needle in name_folded or name_folded in needle:
            return p
    return None


def fetch_luma(city, max_events=80):
    places = get_luma_places()
    place = match_luma_place(city, places)
    if not place:
        print(f"  ! Luma doesn't have a discover page matching '{city}', skipping Luma")
        return []

    events = []
    cursor = ""
    now = datetime.datetime.now(datetime.timezone.utc)
    while len(events) < max_events:
        params = {
            "discover_place_api_id": place["api_id"],
            "pagination_limit": 50,
            "pagination_cursor": cursor,
        }
        try:
            resp = requests.get(
                "https://api.lu.ma/discover/get-paginated-events",
                params=params,
                headers=HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ! skipped a Luma page: {e}")
            break

        entries = data.get("entries", [])
        if not entries:
            break

        for entry in entries:
            ev = entry.get("event") or {}
            start_iso = ev.get("start_at")
            if not start_iso:
                continue
            start_utc = datetime.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            if start_utc < now:  # discover should only return upcoming, but double-check
                continue

            tz_name = ev.get("timezone")
            local_start = start_utc.astimezone(ZoneInfo(tz_name)) if tz_name else start_utc
            time_str = local_start.strftime("%I:%M %p").lstrip("0")
            dates = f"{local_start.strftime('%b %d, %Y')} · {time_str}"

            geo = ev.get("geo_address_info") or {}
            if ev.get("location_type") == "virtual":
                location = "Online"
            else:
                location = geo.get("city_state") or geo.get("city") or ""

            calendar = entry.get("calendar") or {}
            events.append(
                {
                    "source": "Luma",
                    "title": (ev.get("name") or "").strip(),
                    "url": f"https://lu.ma/{ev.get('url', '')}",
                    "location": location,
                    "dates": dates,
                    "sort_date": start_utc.replace(tzinfo=None),
                    "state": "upcoming",
                    "themes": [],
                    "prize": "",
                    "organization": calendar.get("name") or "",
                }
            )

        if not data.get("has_more") or not data.get("next_cursor"):
            break
        cursor = data["next_cursor"]

    return events


# ----------------------------------------------------------------------
# 4. Keep only the events you care about
# ----------------------------------------------------------------------
def keyword_match(haystack, keywords):
    """Word-boundary match so short keywords like 'ai' don't fire on
    substrings inside unrelated words (e.g. 'trail', 'captain')."""
    return any(re.search(rf"\b{re.escape(k)}\b", haystack) for k in keywords if k)


def filter_events(events, config):
    # Devpost's own search already matches events to your city (it's fuzzy and
    # covers nearby venues like "Bay Area" or a named building), so we trust it
    # for location and don't re-filter on the city name here — that would wrongly
    # drop real local events whose venue text doesn't literally say the city.
    # Luma events are already scoped to your city via its own place lookup.
    keywords = [k.lower() for k in config.get("keywords", [])]
    # By default we show ALL upcoming hackathons for your city. Set
    # "require_keyword_match": true in config.json to keep ONLY events that match
    # one of your keywords — this only applies to Devpost; see below for Luma.
    require_kw = config.get("require_keyword_match", False)
    # Luma's feed is general local events (book clubs, concerts, run clubs...),
    # not inherently tech/startup, so it's always narrowed by your keywords
    # plus a built-in list of generic tech/startup terms, regardless of
    # require_keyword_match.
    luma_keywords = list({*keywords, *GENERIC_TECH_KEYWORDS})

    kept = []
    seen_urls = set()
    seen_titles = set()
    for ev in events:
        # Drop anything already finished.
        if ev["state"] == "ended":
            continue

        # De-duplicate by URL, and by normalized title as a safety net for
        # the same event listed on two sources under slightly different URLs.
        if ev["url"] in seen_urls:
            continue
        title_key = re.sub(r"[^a-z0-9]+", "", ev["title"].lower())
        if title_key and title_key in seen_titles:
            continue

        haystack = " ".join(
            [ev["title"], ev["location"], " ".join(ev["themes"])]
        ).lower()

        if ev["source"] == "Luma":
            if not keyword_match(haystack, luma_keywords):
                continue
        elif require_kw and keywords and not keyword_match(haystack, keywords):
            continue

        seen_urls.add(ev["url"])
        if title_key:
            seen_titles.add(title_key)
        kept.append(ev)

    # Upcoming-state events first, then soonest date, then alphabetical.
    kept.sort(
        key=lambda e: (
            e["state"] != "upcoming",
            e["sort_date"] or datetime.datetime.max,
            e["title"].lower(),
        )
    )
    return kept


# ----------------------------------------------------------------------
# 5. Turn the events into a nice web page
# ----------------------------------------------------------------------
def render_html(events, config):
    now = datetime.datetime.now(datetime.timezone.utc)
    updated = now.strftime("%b %d, %Y at %H:%M UTC")
    title = html.escape(config.get("site_title", "Tech Events"))
    subtitle = html.escape(config.get("site_subtitle", ""))
    city = html.escape(config.get("city", ""))

    cards = []
    for ev in events:
        themes = "".join(
            f'<span class="tag">{html.escape(t)}</span>' for t in ev["themes"][:4]
        )
        prize = (
            f'<span class="prize">💰 {html.escape(ev["prize"])}</span>'
            if ev["prize"] and ev["prize"] != "$0"
            else ""
        )
        state_label = "Upcoming" if ev["state"] == "upcoming" else "Open now"
        state_class = "upcoming" if ev["state"] == "upcoming" else "open"
        cards.append(
            f"""
        <a class="card" href="{html.escape(ev['url'])}" target="_blank" rel="noopener">
          <div class="card-top">
            <span class="state {state_class}">{state_label}</span>
            <span class="src">{html.escape(ev['source'])}</span>
          </div>
          <h2>{html.escape(ev['title'])}</h2>
          <p class="meta">📍 {html.escape(ev['location'] or 'Location TBA')}</p>
          <p class="meta">🗓️ {html.escape(ev['dates'] or 'Dates TBA')}</p>
          <div class="tags">{themes}</div>
          {prize}
        </a>"""
        )

    if not cards:
        cards.append(
            '<p class="empty">No matching upcoming events found right now. '
            "Try broadening your keywords or city in <code>config.json</code>.</p>"
        )

    count = len([e for e in events])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #0f1115; --card: #191c23; --line: #262a33;
    --text: #e8eaf0; --muted: #9aa1b0; --accent: #6ea8fe;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.5;
  }}
  header {{
    padding: 48px 24px 24px; max-width: 1100px; margin: 0 auto; text-align: center;
  }}
  header h1 {{ margin: 0 0 8px; font-size: 2rem; }}
  header p {{ margin: 4px 0; color: var(--muted); }}
  .count {{ color: var(--accent); font-weight: 600; }}
  main {{
    max-width: 1100px; margin: 0 auto; padding: 16px 24px 64px;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }}
  .card {{
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 18px; text-decoration: none; color: inherit; transition: .15s;
    display: flex; flex-direction: column; gap: 6px;
  }}
  .card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .card-top {{ display: flex; justify-content: space-between; align-items: center; }}
  .card h2 {{ font-size: 1.1rem; margin: 4px 0; }}
  .meta {{ margin: 0; color: var(--muted); font-size: .9rem; }}
  .state {{ font-size: .72rem; font-weight: 700; padding: 3px 8px; border-radius: 20px; }}
  .state.upcoming {{ background: #1f3a5f; color: #9ec5ff; }}
  .state.open {{ background: #1f4f37; color: #86efac; }}
  .src {{ font-size: .72rem; color: var(--muted); }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }}
  .tag {{ background: #22262f; color: var(--muted); font-size: .72rem;
          padding: 3px 8px; border-radius: 6px; }}
  .prize {{ margin-top: 8px; font-size: .85rem; color: #ffd479; }}
  .empty {{ grid-column: 1/-1; text-align: center; color: var(--muted); padding: 40px; }}
  footer {{ text-align: center; color: var(--muted); font-size: .8rem; padding: 24px; }}
  code {{ background: #22262f; padding: 2px 6px; border-radius: 4px; }}
</style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <p>{subtitle}</p>
    <p>Showing <span class="count">{count}</span> events for <strong>{city}</strong></p>
    <p style="font-size:.8rem">Last updated {updated}</p>
  </header>
  <main>
    {''.join(cards)}
  </main>
  <footer>
    Built automatically with GitHub Actions · Data from Devpost &amp; Luma
  </footer>
</body>
</html>
"""


# ----------------------------------------------------------------------
# 6. Run everything
# ----------------------------------------------------------------------
def main():
    config = load_config()
    city = config.get("city", "")
    print(f"Fetching events for: {city}")

    events = fetch_devpost(city, config.get("max_pages", 6))
    print(f"  found {len(events)} raw Devpost events")

    luma_events = fetch_luma(city, config.get("luma_max_events", 80))
    print(f"  found {len(luma_events)} raw Luma events")
    events += luma_events

    events = filter_events(events, config)
    print(f"  {len(events)} match your filters")

    html_out = render_html(events, config)
    (ROOT / "index.html").write_text(html_out, encoding="utf-8")

    # Also save the raw data in case you want it later.
    (ROOT / "events.json").write_text(
        json.dumps(events, indent=2, default=str), encoding="utf-8"
    )
    print("Wrote index.html and events.json")


if __name__ == "__main__":
    main()
