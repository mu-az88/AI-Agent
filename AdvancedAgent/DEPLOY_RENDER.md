# Plan: deploy the research agent to Render (free tier)

**Status:** deployed and live at https://dev-tools-research-agent.onrender.com (steps 1–7 done; memory and cold-start checks are in step 7).
**Goal:** a public URL where anyone can use the Gradio app, running on Render's free plan, built from the GitHub repo `mu-az88/AI-Agent`.

---

## What you get on the free plan

| | |
|---|---|
| Price | Free (750 instance hours per month, enough for one app running all month) |
| URL | `https://dev-tools-research-agent.onrender.com` (or similar, if that name is taken) |
| Sleep | The app sleeps after **15 minutes** with no visitors. The next visitor waits **30–60 seconds** while it wakes up. |
| Size | Small instance (512 MB RAM, shared CPU). The app should fit, but this is only confirmed once it runs (step 7). |
| Redeploys | Every push to `master` rebuilds and redeploys the app automatically. |

**Side effect on the demo limit:** the "10 free searches per day" counter lives in memory, so it resets every time the app wakes up.
In practice the limit becomes "10 searches per wake-up". Fixing that needs a small database; see "Later" at the bottom.

---

## Who does what

| Step | Who | What |
|---|---|---|
| 1–4 | Claude | Prepare files in the repo (no network, nothing public) |
| 5 | Claude, **after your OK** | Commit and push to GitHub (makes the code public) |
| 6 | **You** | Sign up on Render and create the service from `render.yaml` (a few clicks + paste 2 keys) |
| 7 | Claude + you | Check the build, the live URL and memory use |

---

## Step 1: Pin package versions in `requirements.txt`

Replace the unpinned list with the exact versions the app is tested with locally, so a future library release cannot break the live app:

```
gradio==6.28.0
langchain==1.4.2
langchain-google-genai==4.4.0
langgraph==1.2.11
pydantic==2.13.5
python-dotenv==1.2.3
firecrawl-py==4.44.0
```

`langchain-openai` is removed: nothing in the project imports it, and it would only add install time and memory.

## Step 2: Add `render.yaml` at the repo root

Render reads this "Blueprint" file to create the service, so the setup screen only asks for the two API keys.

```yaml
services:
  - type: web
    name: dev-tools-research-agent
    runtime: python
    plan: free
    rootDir: AdvancedAgent            # the app lives in this subfolder
    buildCommand: pip install -r requirements.txt
    startCommand: python app.py
    autoDeployTrigger: commit         # redeploy on every push to master
    envVars:
      - key: PYTHON_VERSION
        value: "3.12.10"              # same as the local venv (Render's default is newer)
      - key: GRADIO_SERVER_NAME
        value: "0.0.0.0"              # listen on all interfaces, not only localhost
      - key: GRADIO_SERVER_PORT
        value: "10000"                # Render's default port
      - key: DEMO_DAILY_LIMIT
        value: "10"
      - key: GEMINI_API_KEY
        sync: false                   # Render asks for the value during setup; it is never stored in the repo
      - key: FIRECRAWL_API_KEY
        sync: false
```

Checked against Render's Blueprint docs: `autoDeploy` is deprecated (replaced by `autoDeployTrigger`),
env var values must be strings, and Render's default Python is now 3.14, so `PYTHON_VERSION` pins 3.12.10.

No change to `app.py` is needed: Gradio reads `GRADIO_SERVER_NAME` and `GRADIO_SERVER_PORT` from the environment,
and `app.py` already reads the keys and `DEMO_DAILY_LIMIT` with `os.getenv`.

## Step 3: Update the README

- Replace the "Deploying to Hugging Face Spaces" section with a "Deploying to Render" section (short version of this plan),
  and note that Hugging Face now needs a PRO subscription for Gradio Spaces.
- Add `render.yaml` to the project structure list.
- Add the live URL at the top once it exists (step 7).

## Step 4: Safety check before pushing

Already checked:
- `.env`, `venv/` and `__pycache__/` are in `.gitignore`, and none of them has ever been committed.

Checked again right before the commit:
- `git status` shows only the intended files.
- A search of the staged changes finds no API key values.

## Step 5: Commit and push

The Gradio UI, the new look and the width fix are already on GitHub (commit `9135625`, "making gradion UI").
This step adds one more commit with the deployment files: `render.yaml`, the pinned `requirements.txt`,
the README's Render section, this plan and the `.gitignore` update (Streamlit secrets → Gradio cache).
Then `git push origin master`.

## Step 6: Create the service on Render (you)

1. Go to https://render.com and sign up **with GitHub**.
2. Allow Render to access the `mu-az88/AI-Agent` repository (you can allow only this one repo).
3. In the dashboard: **New → Blueprint**, pick `mu-az88/AI-Agent`. Render finds `render.yaml`.
4. Paste the values for `GEMINI_API_KEY` and `FIRECRAWL_API_KEY` (from your local `.env`) and click **Apply**.
5. The first build takes a few minutes (installing the packages).

If Render asks for a payment method even for the free plan, stop and tell me; that would change the plan.

## Step 7: Verify

- **Build log:** the build finishes and the log shows Gradio running on `0.0.0.0:10000`.
- **Page:** the public URL loads, and the theme, the sidebar and the "10 of 10 free searches" status look right.
- **Real search:** one real query, like "vector databases", completes all three steps and shows the result cards.
- **Memory:** in the service's **Metrics** tab, usage stays below the 512 MB limit during a search.
  If it runs out of memory, the fallback is Render's paid Starter plan, or trimming dependencies.
- **Cold start:** after 15+ minutes idle, the page wakes up within about a minute.

---

## Rollback

- To take it offline: **Suspend** or **Delete** the service in the Render dashboard (instant, nothing else affected).
- To undo a bad deploy: push a fix, or use **Manual Deploy → a previous commit** in Render.
- Your API keys can be changed or removed any time under the service's **Environment** tab.

## Later (optional)

- Keep the daily demo count across restarts by storing it in a small free database or key-value store.
- A custom domain (free on Render; you only pay for the domain itself).
