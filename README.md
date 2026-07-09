# Tech Events Tracker 🎟️

A tiny website that **automatically finds upcoming hackathons and tech/startup
events for your city every day** and publishes them as a free web page — all
hosted on GitHub, no server and no monthly bill.

You do **not** need to know how to code to set this up. Follow the steps below
and copy-paste exactly.

---

## How it works (30-second version)

1. **GitHub Actions** (a free robot built into GitHub) wakes up once a day.
2. It runs `build.py`, which pulls current hackathons from **Devpost** and
   general tech/startup meetups from **Luma** for the city you chose in
   `config.json`.
3. It keeps the ones matching your interests and rebuilds `index.html`.
4. **GitHub Pages** serves `index.html` as a real webpage you can bookmark.

```
                          ┌─────────┐
                    ┌────▶│ Devpost │
 ┌─────────────┐    │     └─────────┘
 │GitHub Actions│───▶ build.py
 └─────────────┘    │     ┌─────────┐
                    └────▶│  Luma   │
                          └─────────┘
                                │ writes
                                ▼
                          index.html  ──▶  GitHub Pages (your website)
```

---

## What's in this folder

| File | What it does | Do you edit it? |
|------|--------------|-----------------|
| `config.json` | Your city, interests, page title | ✅ **Yes — this is the only file you need to touch** |
| `build.py` | The program that fetches events and builds the page | ❌ No |
| `index.html` | The finished web page (auto-overwritten each run) | ❌ No |
| `requirements.txt` | Lists the libraries the program needs | ❌ No |
| `.github/workflows/update-events.yml` | The daily-schedule robot | ❌ No |

### Editing `config.json`

```json
{
  "city": "San Francisco",
  "keywords": ["ai", "startup", "web3", "fintech", "hardware", "climate"],
  "site_title": "Tech Events near me",
  "site_subtitle": "Hackathons, tech & startup events, updated daily",
  "max_pages": 6,
  "luma_max_events": 80,
  "require_keyword_match": false
}
```

- **city** — your city name (e.g. `"Bangalore"`, `"London"`, `"Austin"`). Common
  alt-spellings (`"NYC"`, `"Bangalore"`, `"SF"`, `"Bay Area"`...) are recognized
  for the Luma source.
- **keywords** — topics you care about. For Devpost, only used when
  `require_keyword_match` is `true`. For **Luma, keywords are always applied**
  (plus a built-in list of generic tech/startup terms) — Luma's city pages are
  a general local-events feed, so without keyword narrowing you'd get book
  clubs and run clubs mixed in with hackathons.
- **require_keyword_match** — `false` (default) shows **all** upcoming
  Devpost hackathons for your city, narrowed only for Luma (see above). Set it
  to `true` to also narrow Devpost to just your keywords.
- **luma_max_events** — how many Luma events to fetch before filtering
  (default 80). Raise it if your city has a lot of events and you're missing
  ones further out; lower it to speed up the build.

---

## Setup, step by step (about 10 minutes)

### 1. Create a free GitHub account
Go to <https://github.com> and sign up if you don't have an account.

### 2. Create a new repository
- Click the **+** in the top-right → **New repository**.
- Name it something like `my-events`.
- Choose **Public** (required for free GitHub Pages).
- Click **Create repository**.

### 3. Upload these files
- On your new empty repo page, click **“uploading an existing file”**.
- Drag in **all** the files from this folder, **including the `.github` folder**.
  - ⚠️ If dragging the `.github` folder is tricky, see the note at the bottom.
- Click **Commit changes**.

### 4. Let the robot write to your repo
- Go to **Settings → Actions → General**.
- Scroll to **Workflow permissions**.
- Select **“Read and write permissions”** → **Save**.

### 5. Turn on GitHub Pages
- Go to **Settings → Pages**.
- Under **Source**, choose **Deploy from a branch**.
- Branch: **main**, folder: **/ (root)** → **Save**.
- After a minute, this page shows your website address, like
  `https://YOUR-USERNAME.github.io/my-events/`.

### 6. Run it once now (don't wait a day)
- Go to the **Actions** tab.
- Click **“Update events”** on the left → **Run workflow** → **Run workflow**.
- Wait ~1 minute for the green check.
- Open your GitHub Pages address — your events are live! 🎉

From now on it refreshes itself every day automatically.

---

## Common questions

**How do I change my city later?**
Edit `config.json` on GitHub (click the file → the pencil ✏️ icon → change the
text → Commit). Then run the workflow again from the Actions tab, or just wait
for the next daily run.

**What time does it update?**
Once a day at 13:00 UTC. To change it, edit the `cron` line in
`.github/workflows/update-events.yml`. (`"0 13 * * *"` = 13:00 UTC daily.)

**It says no events found.**
Try broadening: fewer/empty `keywords`, or a larger nearby city name (e.g. a
metro area instead of a suburb).

---

## Honest limitations (worth knowing)

- **Sources:** **Devpost** (hackathons) and **Luma** (general tech/startup
  meetups, mixers, demo days). Both are free and keyless, but neither has an
  official public API contract for the endpoints this project uses — they
  could change without notice. Meetup and Eventbrite have mostly closed their
  free public search APIs, so adding them would need an API key stored in
  **GitHub Secrets**. `build.py` is structured so a third source can be added
  later — copy the `fetch_devpost` / `fetch_luma` pattern.
- **Luma coverage is a fixed list of ~80 major cities** (San Francisco, NYC,
  London, Bengaluru, Tokyo, etc. — see `get_luma_places()` if you want the
  full list). If your city isn't on it, you'll still get Devpost hackathons,
  just no Luma meetups; the build won't fail, it just prints a note.
- **Accuracy:** Event data (dates, locations, prizes) comes straight from
  Devpost/Luma and is only as current as their sites. Always click through to
  the event page before making plans.
- **Both sources fail gracefully.** If Devpost or Luma changes their response
  shape or is briefly unreachable, that source is skipped for the run (logged
  to the Action's output) rather than breaking the whole page.

---

## Want to go further?
This is a great candidate for turning into a reusable Claude Skill — if you find
yourself tweaking it often, ask Claude to package the setup steps as a skill so
future edits are one command. You could also add email/Slack notifications when
a new matching event appears.

<sub>Note for step 3: GitHub's drag-and-drop sometimes flattens folders. If the
`.github/workflows/update-events.yml` path gets lost, use **Add file → Create new
file**, type `.github/workflows/update-events.yml` as the name (the slashes make
the folders), and paste the file's contents.</sub>
