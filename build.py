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
import sys
import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.json"


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
    headers = {"User-Agent": "Mozilla/5.0 (event-tracker; personal use)"}
    for page in range(1, max_pages + 1):
        url = "https://devpost.com/api/hackathons"
        params = {"search": city, "page": page}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
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
            events.append(
                {
                    "source": "Devpost",
                    "title": h.get("title", "").strip(),
                    "url": h.get("url", ""),
                    "location": loc.strip(),
                    "dates": h.get("submission_period_dates", "").strip(),
                    "state": h.get("open_state", ""),  # upcoming / open / ended
                    "themes": themes,
                    "prize": strip_html(h.get("prize_amount", "")),
                    "organization": h.get("organization_name") or "",
                }
            )
    return events


def strip_html(text):
    """Devpost wraps prize numbers in HTML tags — clean them up."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


# ----------------------------------------------------------------------
# 3. Keep only the events you care about
# ----------------------------------------------------------------------
def filter_events(events, config):
    keywords = [k.lower() for k in config.get("keywords", [])]
    show_online = config.get("show_online_events", True)
    city = config.get("city", "").lower()

    kept = []
    seen = set()
    for ev in events:
        # Drop anything already finished.
        if ev["state"] == "ended":
            continue

        # De-duplicate by URL.
        if ev["url"] in seen:
            continue

        haystack = " ".join(
            [ev["title"], ev["location"], " ".join(ev["themes"])]
        ).lower()

        # Location check: keep events whose location mentions the city,
        # plus online/virtual events if the user allows them.
        is_online = any(
            w in haystack for w in ["online", "virtual", "worldwide", "global", "anywhere"]
        )
        location_ok = (city in haystack) or (show_online and is_online) or (ev["location"] == "")

        # Interest check: if the user listed keywords, require at least one.
        # (Everything here is already a hackathon, so empty keywords = keep all.)
        interest_ok = (not keywords) or any(k in haystack for k in keywords)

        if location_ok and (interest_ok or not keywords):
            seen.add(ev["url"])
            kept.append(ev)

    # Upcoming events first.
    kept.sort(key=lambda e: (e["state"] != "upcoming", e["title"].lower()))
    return kept


# ----------------------------------------------------------------------
# 4. Turn the events into a nice web page
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
    Built automatically with GitHub Actions · Data from Devpost
  </footer>
</body>
</html>
"""


# ----------------------------------------------------------------------
# 5. Run everything
# ----------------------------------------------------------------------
def main():
    config = load_config()
    city = config.get("city", "")
    print(f"Fetching events for: {city}")

    events = fetch_devpost(city, config.get("max_pages", 6))
    print(f"  found {len(events)} raw events")

    events = filter_events(events, config)
    print(f"  {len(events)} match your filters")

    html_out = render_html(events, config)
    (ROOT / "index.html").write_text(html_out, encoding="utf-8")

    # Also save the raw data in case you want it later.
    (ROOT / "events.json").write_text(
        json.dumps(events, indent=2), encoding="utf-8"
    )
    print("Wrote index.html and events.json")


if __name__ == "__main__":
    main()
