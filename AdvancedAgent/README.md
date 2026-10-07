# AdvancedAgent: Developer Tools Research Agent

An AI agent that researches developer tools for you. It runs in the terminal or as a Gradio web app.

**Try it live:** https://dev-tools-research-agent.onrender.com (free hosting, so the first visit after a quiet spell can take up to a minute to wake up)

You type a topic such as `vector databases` or `CI/CD tools`. The agent searches the web, works out which tools are worth looking at, reads each tool's website, and prints a short report with pricing, open-source status, supported languages, APIs, integrations and a final recommendation.

It is built with:

| Library | What it does in this project |
|---|---|
| **Gemini** (through `langchain-google-genai`) | The LLM that reads web pages and writes the answers |
| **LangChain** (`langchain`, `langchain-core`) | Message types (`SystemMessage`, `HumanMessage`) and structured output (`with_structured_output`) |
| **LangGraph** | Connects the steps of the agent into a workflow |
| **Firecrawl** (`firecrawl-py`) | Searches the web and turns web pages into clean text (markdown) |
| **Pydantic** | Defines the shape of the data passed between steps |
| **python-dotenv** | Loads API keys from the `.env` file |
| **Gradio** | The web interface (`app.py`) |

### The agent's tools

The agent works with three capabilities. It does **not** use LLM tool calling (where the model decides which tool to call next). The code calls each tool in a fixed order, and the model only reads text and writes answers:

| Tool | Provided by | Used for |
|---|---|---|
| **Web search** | Firecrawl `search` (`FirecrawlService.search_companies`) | Finding comparison articles (step 1) and each tool's official site (step 2) |
| **Web scraping** | Firecrawl `scrape_url` (`FirecrawlService.scrape_company_pages`) | Turning a web page into markdown text the LLM can read |
| **LLM reasoning** | Gemini `gemini-3.5-flash-lite` (`ChatGoogleGenerativeAI`) | Picking tool names out of articles (free text), filling in a structured form per tool (structured output), writing the final recommendation (free text) |

---

## Example

```
Developer Tools Query: vector databases
finding articles about vector databases
Extracted Tools: Pinecone, Milvus, Zilliz Cloud, Turbopuffer, Redis
Researching specific tools: Pinecone, Milvus, Zilliz Cloud, Turbopuffer
Generating recommendations...

📊 Results for: vector databases
============================================================

1. 🏢 Pinecone
   🌐 Website: https://www.pinecone.io/pricing/
   💰 Pricing: Freemium
   📖 Open Source: False
   🛠️  Tech Stack: Vector Database, Dense Indexes, Sparse Indexes, Full-Text Indexes
   🔌 API: ✅ Available
   🔗 Integrations: AWS, Google Cloud, Microsoft, Prometheus
   📝 Description: Pinecone is a fully managed vector database service ...

2. 🏢 Milvus
   ...

Developer Recommendations:
----------------------------------------
For most production AI applications, Pinecone is the best choice because ...
```

---

## Project structure

```
render.yaml              # (repo root) Render deployment settings
AdvancedAgent/
├── main.py              # Terminal version: asks for queries and prints results
├── app.py               # Web version: the same agent with a Gradio interface
├── ui_theme.py          # The web app's look: dark colour palette, fonts and rounded styling
├── requirements.txt     # Python packages to install (exact versions)
├── DEPLOY_RENDER.md     # Step-by-step plan for deploying to Render
├── .env                 # Your API keys (you create this; never share or commit it)
└── src/
    ├── __init__.py      # Makes "src" a Python package so main.py can import from it
    ├── workflow.py      # The agent itself: the three steps and how they connect
    ├── firecrawl.py     # Small wrapper around Firecrawl for searching and scraping
    ├── models.py        # Pydantic data models (the agent's "memory" and the LLM's output format)
    └── prompts.py       # All the text instructions sent to the LLM
```

---

## How it works

The agent is a **LangGraph workflow** with three steps (called *nodes*). They run in a fixed order, and each one reads from and writes to a shared object called the **state**.

```
   your query
       │
       ▼
┌──────────────────────┐
│ 1. extracted_tools   │  Search for comparison articles → scrape them →
│                      │  ask Gemini: "which tools are mentioned here?"
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 2. research          │  For each tool (up to 4): find its official site →
│                      │  scrape it → ask Gemini to fill in a structured form
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 3. analysis          │  Send all the collected data to Gemini →
│                      │  get a short 3–4 sentence recommendation
└──────────┬───────────┘
           ▼
     printed report
```

### The shared state (`ResearchState` in `src/models.py`)

Think of the state as a notebook that every step can read and write:

| Field | Filled in by | Contents |
|---|---|---|
| `query` | `main.py` | What the user typed |
| `extracted_tools` | Step 1 | Tool names found in articles, e.g. `["Pinecone", "Milvus"]` |
| `companies` | Step 2 | One `CompanyInfo` object per researched tool |
| `analysis` | Step 3 | The final recommendation text |

Each step returns a small dictionary such as `{"companies": [...]}`, and LangGraph merges it into the state automatically.

### Step 1: Extract tools (`_extract_tool_step`)

1. Searches the web for `"<query> tools comparison best alternatives"` and takes the top 3 results.
2. Scrapes each result and keeps the first 1,500 characters of its text.
3. Sends that text to Gemini with the `TOOL_EXTRACTION` prompts, asking for up to 5 real product names, one per line.
4. Splits the answer into a Python list.

If this step fails or finds nothing, `extracted_tools` stays empty.

### Step 2: Research each tool (`_research_step`)

1. Takes the first 4 extracted tools. If step 1 found none, it falls back to a plain web search on the query and uses the page titles instead.
2. For each tool:
   - Searches for `"<tool> official site"` and takes the first result.
   - Scrapes that page.
   - Calls `_analyze_company_content`, which asks Gemini to fill in a `CompanyAnalysis` form (pricing, open source, tech stack, API, languages, integrations, description).
3. Saves each result as a `CompanyInfo` object.

Edge cases:

- If the official-site search returns nothing, that tool is **dropped** from the results.
- If the site can't be scraped, the tool is kept with only its name, URL and the search snippet as its description. Pricing and the other fields stay empty.

**Structured output** is the important idea here. `self.llm.with_structured_output(CompanyAnalysis)` tells Gemini to reply with data that exactly matches the Pydantic model, not free text. You get a real Python object back (`analysis.pricing_model`, `analysis.api_available`, ...) with no text parsing.

If the analysis fails, a safe default is used with the description set to `ANALYSIS_FAILED`, and `main.py` hides that description when printing.

### Step 3: Recommend (`_analyze_step`)

Turns every `CompanyInfo` into JSON, sends it to Gemini with the `RECOMMENDATIONS` prompts, and stores the short answer in `state.analysis`.

### Printing the results (`main.py`)

`main()` loops forever: it reads a query, calls `workflow.run(query)`, and prints each company's fields and then the recommendation. Empty fields are skipped. Type `exit` or `quit` to stop.

---

## The files in more detail

### `main.py`: terminal version

| Name | Purpose |
|---|---|
| `load_dotenv()` | Loads `GEMINI_API_KEY` and `FIRECRAWL_API_KEY` from `.env` |
| `main()` | Creates one `Workflow`, then loops: reads a query, runs it and prints each tool (top 5 tech stack items, top 5 languages, top 4 integrations) followed by the recommendation. `exit` or `quit` stops it |

### `src/__init__.py`

Empty file. It makes `src` a package so `from src.workflow import Workflow` works.

### `src/firecrawl.py`: `FirecrawlService`

It uses `V1FirecrawlApp`, the client for Firecrawl's v1 API that ships with `firecrawl-py` 4.x.

| Method | Purpose |
|---|---|
| `__init__` | Uses the key passed in, or `FIRECRAWL_API_KEY` from `.env`, and stops with an error if neither exists |
| `search_companies(query, num_results)` | Web search. **Note:** it always appends `" company pricing"` to the query. Returns `[]` on error |
| `scrape_company_pages(url)` | Downloads one page as markdown. Returns `None` on error |

Both methods catch errors and return an empty result instead of crashing, so one bad website doesn't stop the whole run.

### `src/models.py`

| Name | Purpose |
|---|---|
| `ANALYSIS_FAILED` | Shared text used when analysis fails, so `workflow.py` and `main.py` always agree |
| `CompanyAnalysis` | The "form" Gemini fills in for one tool (structured output) |
| `CompanyInfo` | Everything known about one tool (search result + analysis) |
| `ResearchState` | The shared state passed through the workflow (`search_results` is declared but never used) |

### `src/prompts.py`: `DeveloperToolsPrompts`

Keeps all LLM instructions in one place. Each task has two parts:

- a **system prompt** (a constant), which tells the model *who it is*, e.g. "You are a tech researcher".
- a **user prompt** (a function), which builds the actual request with the query and scraped content inserted.

| Task | System prompt | User prompt function |
|---|---|---|
| Find tool names in articles | `TOOL_EXTRACTION_SYSTEM` | `tool_extraction_user(query, content)` |
| Analyze one tool's website | `TOOL_ANALYSIS_SYSTEM` | `tool_analysis_user(company_name, content)` (uses the first 2,500 characters) |
| Final recommendation | `RECOMMENDATIONS_SYSTEM` | `recommendations_user(query, company_data)` |

To change how the agent "thinks", edit this file first.

### `src/workflow.py`: `Workflow`

| Method | Purpose |
|---|---|
| `__init__` | Creates the Firecrawl service, the Gemini model and the prompts, then builds the graph. API keys can be passed in, otherwise they come from `.env` |
| `_build_workflow` | Registers the 3 nodes, sets the entry point and connects them in order |
| `_extract_tool_step` | Step 1 |
| `_research_step` | Step 2 |
| `_analyze_company_content` | Helper for step 2: structured analysis of one tool |
| `_analyze_step` | Step 3 |
| `run(query, on_step=None)` | Public entry point: runs the whole graph and returns the final `ResearchState`. The optional `on_step` function is called after each step, which is how the web app shows progress |

`run` uses `self.workflow.stream(..., stream_mode="updates")` instead of `invoke`, so it gets each node's output as soon as that node finishes and can merge it into its own copy of the state.

### `app.py`: Gradio web app

| Name | Purpose |
|---|---|
| `get_owner_key(name)` | Reads one of the app owner's settings from the environment (`.env` locally, Render environment variables when deployed) |
| `DEMO_DAILY_LIMIT` | Searches per day allowed on the owner's keys (env var, default 3) |
| `demo_usage` | In-memory counter `{date, count, lock}` shared by every visitor. The lock keeps simultaneous requests from miscounting |
| `demo_runs_left()` | Searches left today. Resets the counter when the date changes |
| `use_demo_run()` | Uses up one demo search. Returns `False` if the limit is reached |
| `key_status(gemini, firecrawl)` | Sidebar text: "using your keys" or "N of M free searches left" |
| `format_company(company)` | Builds one tool's markdown card: name, link, a pricing / open source / API table, description, stack, languages, integrations. Escapes `\|` so values can't break the table |
| `card(markdown, css_class)` | Wraps markdown in a `<div>` so it gets the rounded card style |
| `format_result(result)` | Full results: recommendation card first, then one card per tool, or a warning if no tools were found |
| `research(query, gemini, firecrawl)` | The event handler (a generator). It validates input, chooses visitor or owner keys, enforces the demo limit, runs `Workflow` in a background thread, and yields progress, results, key status and button state as each step finishes |
| `demo` (`gr.Blocks`) | The layout: sidebar with two password fields for keys, hero header, search bar, terminal-style progress box, results area and footer. Two `gr.on` events connect it to `research` and `key_status` |

`demo.launch(theme=THEME, css=CSS, js=FORCE_DARK_JS)` starts the server on port 7860, or on the host and port in `GRADIO_SERVER_NAME` / `GRADIO_SERVER_PORT`.

### `ui_theme.py`: web app styling

| Name | Purpose |
|---|---|
| Palette constants (`BG`, `SURFACE`, `GREEN`, `CYAN`, `VIOLET`, ...) | Colours for a dark "terminal" look with a phosphor-green accent |
| `dark_everywhere(**variables)` | Sets each Gradio theme variable *and* its `_dark` variant to the same value, so the app looks the same whatever the visitor's system theme is |
| `THEME` | A `gr.themes.Base` theme: Inter and JetBrains Mono fonts, rounded blocks, pill buttons with a green-to-cyan gradient, dark inputs and tables |
| `CSS` | Extra styles: fixed page width (stops the sidebar overlapping the search bar), hero header, search bar, the `agent.log` terminal window, result cards, a highlighted recommendation card, sidebar, footer and a phone layout |
| `FORCE_DARK_JS` | Adds the `dark` class to the page so Gradio's built-in components also use dark mode |

### `requirements.txt`

Exact versions of the 7 packages the app is tested with: `gradio`, `langchain`, `langchain-google-genai`, `langgraph`, `pydantic`, `python-dotenv` and `firecrawl-py`. They are pinned so the deployed app can't break when a new version comes out.

### `DEPLOY_RENDER.md` and `render.yaml`

`render.yaml` (in the repo root) is the Render Blueprint that describes the web service. `DEPLOY_RENDER.md` is the step-by-step deployment plan with the reasons behind each setting. Both are summarised in [Deploying to Render](#deploying-to-render-free) below.

---

## Setup

### 1. Requirements

- Python 3.10 or newer (developed with 3.12)
- A **Gemini API key**: https://aistudio.google.com/apikey
- A **Firecrawl API key**: https://www.firecrawl.dev

### 2. Create a virtual environment and install packages

From inside the `AdvancedAgent` folder:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate         # macOS / Linux

pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, skip activation and use `.\venv\Scripts\python.exe` instead of `python` in the commands below.

### 3. Add your API keys

Create a file named `.env` in the `AdvancedAgent` folder:

```
GEMINI_API_KEY=your-gemini-key-here
FIRECRAWL_API_KEY=your-firecrawl-key-here
```

`.env` is listed in `.gitignore`. Never commit it or send it to anyone.

### 4. Run

**Terminal version:**

```powershell
python main.py
```

**Web version:**

```powershell
python app.py
```

Then open http://127.0.0.1:7860 in your browser. Stop the app with `Ctrl+C` in the terminal.

If you want the app to reload automatically every time you save a file while you work on it, run `gradio app.py` instead.

Run both **from inside the `AdvancedAgent` folder**, because they import `src.workflow` and `.env` is loaded from the current folder.

---

## The web app (`app.py`)

The web app uses exactly the same `Workflow` as the terminal version. It only adds an interface on top:

- **A search box.** Type a topic and click **Research**.
- **Live progress.** A status box shows each step as it finishes, using the `on_step` callback of `Workflow.run`.
- **Result cards.** One card per tool with pricing, open source, API, tech stack, languages and integrations, plus the recommendation at the top.
- **Optional visitor API keys (sidebar).** When the app is public, every search costs API quota. Visitors can enter their own Gemini and Firecrawl keys for unlimited searches. Their keys are only used for that request and are not saved.
- **A daily demo limit.** Visitors without keys share a small number of searches per day that use *your* keys (`DEMO_DAILY_LIMIT`, default 3, set to 10 on Render). The counter is kept in memory, so it also resets whenever the app restarts.

Two Gradio ideas worth knowing:

- **Events connect components to Python functions.** `gr.on(triggers=[research_button.click, query.submit], fn=research, ...)` means "when the button is clicked or Enter is pressed, call `research` with these inputs and put its return values into these outputs".
- **Generator functions stream updates.** `research` uses `yield` instead of `return`, and every `yield` updates the page straight away. The workflow runs in a background thread and sends each finished step through a queue, so `research` can keep yielding progress while the agent works.

The demo usage counter is a normal module-level variable, so it is shared by every visitor. Gradio also queues requests, so if several people search at once they wait in line and see their position in the queue.

---

## Deploying to Render (free)

The app is deployed on [Render](https://render.com)'s free plan straight from this GitHub repo.
The service is described in `render.yaml` at the root of the repo, so Render sets it up from that file (a "Blueprint").
The full plan with the reasons behind each setting is in `DEPLOY_RENDER.md`.

1. Sign up at https://render.com **with GitHub** and give Render access to this repository.
2. In the dashboard click **New → Blueprint** and pick the repository. Render reads `render.yaml`.
3. Paste your `GEMINI_API_KEY` and `FIRECRAWL_API_KEY` when asked, and click **Apply**. Never commit these keys.
4. The first build takes a few minutes while the packages install from `requirements.txt`.
   After that, every push to `master` redeploys the app automatically.

What `render.yaml` sets up:

| Setting | Value | Why |
|---|---|---|
| `rootDir` | `AdvancedAgent` | The app lives in this subfolder of the repo |
| `startCommand` | `python app.py` | Same command as running it locally |
| `PYTHON_VERSION` | `3.12.10` | Same version as the local venv (Render's default is newer) |
| `GRADIO_SERVER_NAME` / `GRADIO_SERVER_PORT` | `0.0.0.0` / `10000` | Gradio reads these, so it accepts outside connections on Render's port. No code change needed |
| `DEMO_DAILY_LIMIT` | `10` | Free searches per day that use your keys |

Render passes these to the app as environment variables, so `app.py` reads them with `os.getenv`, exactly like the values from `.env` when you run it locally.

Things to know about the free plan:

- The app **sleeps after 15 minutes** without visitors. The next visitor waits 30 to 60 seconds while it wakes up.
- The demo counter is kept in memory, so it resets every time the app wakes up.
- `requirements.txt` pins exact versions, so a new library release can't break the live app. Update them on purpose, test locally, then push.

(Hugging Face Spaces used to be the usual free host for Gradio apps, but Gradio Spaces on free hardware now need a PRO subscription.)

---

## Configuration

| What | Where | Default |
|---|---|---|
| Gemini model | `src/workflow.py`, `model=` in `__init__` | `gemini-3.5-flash-lite` |
| Number of articles read in step 1 | `_extract_tool_step`, `num_results=3` | 3 |
| Number of tools researched | `_research_step`, `extracted_tools[:4]` | 4 |
| Text kept per article | `_extract_tool_step`, `[:1500]` | 1,500 characters |
| Text sent for tool analysis | `prompts.py`, `content[:2500]` | 2,500 characters |

**About model choice:** Lite models are cheaper and usually have larger free quotas, but they are worse at picking the right tool names. Larger models give better results but hit free-tier limits sooner.

---

## API usage per query

One query makes roughly:

- **Gemini:** 1 (extract) + up to 4 (analysis) + 1 (recommendation) = **about 6 requests**
- **Firecrawl:** 1 search + 3 scrapes in step 1, then 1 search + 1 scrape per tool in step 2 = **about 12 requests**

Keep this in mind on free plans.

---

## Troubleshooting

| Message | Meaning | What to do |
|---|---|---|
| `429 RESOURCE_EXHAUSTED ... free_tier_requests` | You used up the Gemini free quota for this model (often a **daily** limit) | Wait for the reset, switch to another model in `workflow.py`, or enable billing. Check your limits at https://aistudio.google.com/rate-limit |
| `Website Not Supported: Failed to scrape URL` | Firecrawl can't scrape that site (e.g. Reddit) | Nothing. The agent skips it and continues |
| `UserWarning: ... temperature will be ignored` followed by `request = self._build_request_config(` | The model ignores the `temperature` setting. The second line is part of the same warning | Harmless. Remove `temperature=0.1` in `workflow.py` to hide it |
| `Direct use of automatic function calling (AFC) ... is not recommended` | An informational message from the Google library | Harmless |
| `missing FIRECRAWL_API_KEY` | `.env` is missing or not in the current folder | Create `.env` and run from the `AdvancedAgent` folder |
| `ModuleNotFoundError: No module named 'src'` | You ran `main.py` from a different folder | `cd` into `AdvancedAgent` first |
| Web app: "Today's free demo searches are used up" | The daily demo limit was reached | Enter your own keys in the sidebar, or raise `DEMO_DAILY_LIMIT` in the secrets |
| Irrelevant tools in the results | The scraped articles were off-topic, or the model misread them | Rephrase the query, or try a larger model |

Every step catches its own errors. If Gemini fails during the final recommendation (e.g. quota exceeded), the tool results are still shown with a short message in place of the recommendation.

---

## Ideas for practice

1. Save the demo usage counter to a file or database, so it survives app restarts.
2. Print `developer_experience_rating` and `competitors`. They exist in `CompanyInfo` but are never filled in, so add them to `CompanyAnalysis` and the prompt.
3. Make the number of researched tools a setting instead of the hard-coded `[:4]`.
4. Add a conditional edge in LangGraph that skips step 2 when step 1 finds nothing, instead of the fallback search.
5. Save each report to a markdown file as well as printing it.
6. Add an option to switch between Gemini and another provider (e.g. install `langchain-openai` and use `ChatOpenAI`). Only `Workflow.__init__` needs to change.
