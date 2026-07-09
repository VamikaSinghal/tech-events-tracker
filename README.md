# Tech Events Tracker 🎟️

A tiny website that **automatically finds upcoming hackathons and tech/startup
events for your city every day** and publishes them as a free web page — all
hosted on GitHub, no server and no monthly bill.

You do **not** need to know how to code to set this up. Follow the steps below
and copy-paste exactly.

---

## How it works (30-second version)

1. **GitHub Actions** (a free robot built into GitHub) wakes up once a day.
2. It runs `build.py`, which pulls current hackathons from **Devpost** for the
   city you chose in `config.json`.
3. It keeps the ones matching your interests and rebuilds `index.html`.
4. **GitHub Pages** serves `index.html` as a real webpage you can bookmark.

```
 ┌─────────────┐   daily   ┌──────────┐   fetch   ┌─────────┐
 │GitHub Actions│ ───────▶ │ build.py │ ───────▶  │ Devpost │
 └─────────────┘           └────┬─────┘           └─────────┘
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
| `requirements.txt` | Lists the one library the program needs | ❌ No |
| `.github/workflows/update-events.yml` | The daily-schedule robot | ❌ No |

### Editing `config.json`

```json
{
  "city": "San Francisco",
  "keywords": ["ai", "startup", "web3", "fintech", "hardware", "climate"],
  "site_title": "Tech Events near me",
  "site_subtitle": "Hackathons, tech & startup events, updated daily",
  "max_pages": 6,
  "require_keyword_match": false
}
```

- **city** — your city name (e.g. `"Bangalore"`, `"London"`, `"Austin"`).
- **keywords** — topics you care about (used only when the setting below is `true`).
- **require_keyword_match** — `false` (default) shows **all** upcoming hackathons
  for your city. Set it to `true` to show **only** events matching one of your
  keywords — a shorter, more selective list.

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
Try broadening: fewer/empty `keywords`, a larger nearby city name, or set
`show_online_events` to `true`.

---

## Honest limitations (worth knowing)

- **Source:** This currently pulls from **Devpost**, which is excellent for
  **hackathons** but is not a full "all tech & startup events" feed. Broader
  event platforms (Meetup, Eventbrite, Luma) have mostly closed or restricted
  their free public search APIs, so adding them reliably means either an API key
  or fragile web-scraping. `build.py` is structured so a second source can be
  added later — look for the `fetch_devpost` function and copy its pattern.
- **Accuracy:** Event data (dates, locations, prizes) comes straight from
  Devpost and is only as current as their site. Always click through to the
  event page before making plans.
- **Devpost has no official public API contract** for this endpoint, so if they
  change it, the fetch step may need updating. The script fails gracefully (it
  just shows the previous list) rather than breaking your page.

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
