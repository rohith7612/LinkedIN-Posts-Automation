# LinkedIn AI News Automation

Daily pipeline: collect AI news → clean/dedupe → lightweight verification →
NotebookLM infographic generation (manual step) → GPT-5 nano caption → post to
LinkedIn.

## Why this isn't 100% hands-off

Google NotebookLM has **no public API**. There is no way to programmatically
feed it news and pull out an infographic. So the pipeline is split into two
phases:

- **Phase 1** (automated, runs on a daily schedule): collects news, cleans and
  dedupes it, runs verification, writes a digest, copies it to your clipboard,
  and opens NotebookLM in your browser.
- **You**: paste the digest into NotebookLM as a source, generate a Video
  Overview / Mind Map / whatever visual output you like, and save the exported
  image(s) into `data/<today's date>/infographics/`.
- **Phase 2** (you trigger it, e.g. by double-clicking `run_phase2.bat`):
  writes the LinkedIn caption and publishes the post with your images.

This takes about a minute of manual effort per day in exchange for using
NotebookLM specifically, as you asked. If you'd rather have a fully unattended
pipeline, the only way is to swap NotebookLM for a true API-driven image
generator — say the word and I'll wire that in instead.

## Also be aware

- **Verification is a plausibility check, not fact-checking.** It combines (a)
  how many independent outlets ran the same story and (b) a GPT-5 nano read
  for internal consistency / unsourced claims. It cannot browse the live web
  to confirm facts. Treat "CAUTION" flags as "read before you post," not "false."
- **LinkedIn's API evolves.** The endpoints/version header in
  `src/config.py` (`LINKEDIN_API_VERSION`) and `src/linkedin_post.py` reflect
  the Posts API structure at build time. If posting starts failing with a
  version or schema error, check LinkedIn's current API docs and adjust.

---

## 1. One-time setup

### 1a. Install Python dependencies

```
cd "LinkedIn Posts Automation"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 1b. Get an OpenAI API key

1. Go to https://platform.openai.com/api-keys and create a key.
2. Make sure your account has access to `gpt-5-nano` (it's OpenAI's cheapest
   GPT-5 tier — this pipeline's OpenAI cost per day is a few thousand tokens,
   fractions of a cent).

### 1c. Create a LinkedIn Developer App (needed for posting)

1. Go to https://www.linkedin.com/developers/apps → **Create app**.
2. Fill in app name, link it to a **Company Page you administer** (LinkedIn
   requires every app to be tied to a page, even if you're posting to your
   personal profile).
3. Under the app's **Products** tab, request **"Share on LinkedIn"** and
   **"Sign In with LinkedIn using OpenID Connect"**. These are usually
   auto-approved for personal-profile posting scopes (`w_member_social`,
   `openid`, `profile`).
4. Under **Auth**, add this exact redirect URL:
   `http://localhost:8765/callback`
5. Copy the **Client ID** and **Client Secret** from the Auth tab.

### 1d. Fill in `.env`

Copy `.env.example` to `.env` in the project root and fill in:

```
OPENAI_API_KEY=sk-...
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_REDIRECT_URI=http://localhost:8765/callback
```

### 1e. Authorize LinkedIn (one-time, and again every ~60 days)

```
run_auth.bat
```

This opens your browser to LinkedIn's consent screen, you approve, and it
saves a token to `data/linkedin_token.json`. LinkedIn access tokens expire
after ~60 days — just rerun this when `linkedin_post.py` tells you it's expired.

---

## 2. Daily workflow

### Automated part (Phase 1)

Set up a Windows Task Scheduler entry to run `run_phase1.bat` once a day
(e.g. 7:00 AM):

1. Open **Task Scheduler** → **Create Basic Task**.
2. Name it "LinkedIn AI News – Phase 1".
3. Trigger: **Daily**, pick a time.
4. Action: **Start a program** → Browse to
   `...\LinkedIn Posts Automation\run_phase1.bat`.
5. Finish. (Check "Run whether user is logged on or not" only if you're
   comfortable storing your Windows password for the task — otherwise your
   PC just needs to be logged in and awake at the scheduled time.)

This step:
- Pulls the last ~30 hours of entries from the RSS feeds in `config/feeds.yaml`.
- Cleans HTML, clusters near-duplicate headlines from different outlets, and
  keeps the top 5 stories (configurable in `feeds.yaml` → `settings`).
- Verifies each (corroboration count + GPT-5 nano sanity check).
- Writes `data/<date>/digest.md`, copies it to your clipboard, and opens
  NotebookLM.

### Manual part (you, ~1 minute)

In the NotebookLM tab:
1. New notebook → **Add source** → **Paste text** → paste (already on your
   clipboard) → Insert.
2. In the **Studio** panel, generate a **Video Overview** (or Mind Map, or
   whichever visual format you prefer) covering the digest.
3. Export/download the image(s) it produces.
4. Save them into `data/<date>/infographics/` (the folder already exists,
   created by phase 1).

### Automated part (Phase 2)

Double-click `run_phase2.bat` (or run `python src/pipeline.py phase2`). This:
- Generates a LinkedIn caption from the verified stories using GPT-5 nano.
- Uploads every image in `infographics/` and publishes the post to your
  personal LinkedIn profile.
- Logs the result to `data/<date>/post_log.json`.

---

## 3. What you must supply manually (summary)

| Item | Where it goes | Notes |
|---|---|---|
| OpenAI API key | `.env` → `OPENAI_API_KEY` | Needs `gpt-5-nano` access |
| LinkedIn Client ID/Secret | `.env` | From your LinkedIn Developer App |
| LinkedIn OAuth consent | run `run_auth.bat` once, then every ~60 days | Opens browser, one click |
| NotebookLM infographic generation | Daily, ~1 min | Paste digest, generate Video Overview, export images to `infographics/` |
| Task Scheduler entry | Windows Task Scheduler | Points at `run_phase1.bat`, once a day |

## 4. Project layout

```
config/feeds.yaml       RSS source list + tunables (lookback window, top-N, dedupe threshold)
src/config.py            paths, env vars, model name
src/collect.py           step 1: fetch RSS feeds
src/preprocess.py        step 2: clean HTML, dedupe/cluster, rank, select top N
src/verify.py            step 3: corroboration + GPT-5 nano plausibility check
src/notebooklm_prep.py   step 4: build digest, open NotebookLM, hand off
src/describe.py          step 5: GPT-5 nano caption generation
src/linkedin_auth.py     one-time OAuth flow
src/linkedin_post.py     step 6: upload images + publish post
src/pipeline.py          orchestrator (phase1 / phase2 / auth)
data/<date>/             per-day working files (gitignored)
run_phase1.bat           Task Scheduler target
run_phase2.bat           double-click after infographics are ready
run_auth.bat             (re)authorize LinkedIn
```

## 5. Tuning

Edit `config/feeds.yaml`:
- `feeds`: add/remove RSS sources.
- `lookback_hours`: how far back counts as "today's news."
- `top_n_stories`: how many stories make it into the digest/post.
- `dedupe_similarity_threshold`: how similar two headlines must be (0-100) to
  be treated as the same story from different outlets.
