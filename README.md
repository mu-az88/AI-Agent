# AI-Agent

AI agents built with **Google Gemini**, **LangGraph** and **Firecrawl**. The repo contains:

1. **[AdvancedAgent](AdvancedAgent/README.md)**, the main project: a developer tools research agent with a web app, deployed live.
2. **[SimpleAgent](SimpleAgent/README.md)**: two small learning scripts that show how tool-calling agents work.

---

## ⭐ AdvancedAgent: Developer Tools Research Agent

**Try it live:** https://dev-tools-research-agent.onrender.com
(It's on free hosting, so the first visit after a quiet spell can take up to a minute to wake up.)

Type a topic such as `vector databases`, `CI/CD tools` or `headless CMS`. The agent:

1. **searches the web** for comparison articles and asks Gemini which tools they mention,
2. **reads each tool's official website** (up to 4 tools) and fills in a structured profile: pricing model, open source or not, tech stack, API availability, supported languages and integrations,
3. **writes a short recommendation**: which tool is best for you, what it costs and why.

You can run it as a terminal program (`main.py`) or as a Gradio web app (`app.py`). The web app shows live progress in a terminal-style log and displays one card per tool. Visitors can use a few free searches per day or enter their own API keys for unlimited use.

```
   your query
       │
       ▼
 1. extract tools   ── Firecrawl search + scrape → Gemini picks tool names
       │
       ▼
 2. research        ── per tool: find official site → scrape → Gemini fills a Pydantic form
       │
       ▼
 3. analysis        ── Gemini writes a 3–4 sentence recommendation
       │
       ▼
   report (terminal or web cards)
```

| Built with | Role |
|---|---|
| **LangGraph** | Runs the three steps as a state graph that shares one `ResearchState` |
| **Gemini** (`langchain-google-genai`) | Reads pages, extracts tool names, returns **structured output**, writes the recommendation |
| **Firecrawl** | Web search and page-to-markdown scraping |
| **Pydantic** | Typed models for the state and for the LLM's structured answers |
| **Gradio** | Web interface with streaming progress and a custom dark theme |
| **Render** | Free hosting, deployed from `render.yaml` on every push to `master` |

**Quick start:**

```powershell
cd AdvancedAgent
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# create .env with GEMINI_API_KEY=... and FIRECRAWL_API_KEY=...
python app.py      # web app on http://127.0.0.1:7860
python main.py     # or the terminal version
```

➡️ The full documentation, covering every file, the workflow, configuration, deployment and troubleshooting, is in **[AdvancedAgent/README.md](AdvancedAgent/README.md)**.

---

## SimpleAgent: learning examples

Two short scripts that came before the AdvancedAgent. Here the **LLM decides** which tool to call. The AdvancedAgent instead runs a fixed pipeline in code.

| Script | What it does |
|---|---|
| `agent.py` | Terminal chat agent using the `google-genai` SDK. Gemini automatically calls a **calculator** or a **clock** tool when needed, and remembers the conversation |
| `agent2.py` | Starts the **Firecrawl MCP server**, loads its web tools and builds a LangGraph **ReAct** agent with them plus the calculator. Unfinished: it never sends the agent a message |

➡️ See **[SimpleAgent/README.md](SimpleAgent/README.md)** for how they work and how to run them.

---

## Repository layout

```
AI-Agent/
├── README.md            # This overview
├── render.yaml          # Render deployment Blueprint for the AdvancedAgent web app
├── .gitignore           # Keeps .env, venv/, __pycache__/ and .gradio/ out of git
├── AdvancedAgent/       # ⭐ Main project: research agent (terminal + Gradio web app)
│   ├── main.py, app.py, ui_theme.py, requirements.txt, DEPLOY_RENDER.md
│   └── src/             # workflow.py, firecrawl.py, models.py, prompts.py
└── SimpleAgent/         # Learning examples
    ├── agent.py
    └── agent2.py
```

## API keys

Both projects need a **Gemini API key** (https://aistudio.google.com/apikey). The AdvancedAgent and `agent2.py` also need a **Firecrawl API key** (https://www.firecrawl.dev). Put them in a `.env` file as described in each project's README. `.env` is git-ignored, so never commit your keys.
