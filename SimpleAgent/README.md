# SimpleAgent: Learning Examples for Tool-Using Agents

Two small scripts that show the basic idea behind an AI agent: **an LLM that can decide to call tools**. They are learning steps on the way to the [AdvancedAgent](../AdvancedAgent/README.md), and they are kept short on purpose.

| Script | What it shows | Status |
|---|---|---|
| `agent.py` | A terminal chat agent. Gemini chooses on its own when to use a calculator or a clock | Complete and runnable |
| `agent2.py` | Connecting an agent to an **MCP server** (Firecrawl) to get web tools, then building a LangGraph ReAct agent | Unfinished: it builds the agent but never sends it a message |

It is built with:

| Library | Used in | What it does |
|---|---|---|
| **Gemini** through `google-genai` (Google's official SDK) | `agent.py` | The LLM, plus *automatic function calling* |
| **Gemini** through `langchain-google-genai` | `agent2.py` | The same LLM, wrapped for LangChain/LangGraph |
| **LangGraph** (`create_react_agent`) | `agent2.py` | A ready-made "reason → call tool → read result → repeat" agent loop |
| **MCP** (`mcp`) and **`langchain-mcp-adapters`** | `agent2.py` | Starts an MCP server and turns its tools into LangChain tools |
| **Firecrawl MCP server** (`firecrawl-mcp`, run with `npx`) | `agent2.py` | Provides web search and scraping tools |
| **python-dotenv** | both | Loads API keys from `.env` |

---

## How this differs from the AdvancedAgent

These scripts use **tool calling**: the model reads the user's message and decides *which* tool to call (if any) and with what arguments. The AdvancedAgent works the other way round. Its code runs a fixed pipeline (search → scrape → analyze → recommend) and the model only reads text and writes answers.

| | SimpleAgent | AdvancedAgent |
|---|---|---|
| Who decides what happens next | The LLM | The code (a fixed LangGraph graph) |
| Tools | Calculator, clock, Firecrawl via MCP | Firecrawl via its Python SDK |
| Output | Free-form chat answers | Structured report (Pydantic models) |
| Interface | Terminal only | Terminal and Gradio web app |

---

## Project structure

```
SimpleAgent/
├── agent.py      # Chat agent with a calculator and a clock (google-genai SDK)
├── agent2.py     # Agent skeleton with Firecrawl MCP tools (LangGraph + MCP)
└── README.md     # This file
```

There is no `requirements.txt` in this folder. The packages are listed under [Setup](#setup).

---

## `agent.py`: chat agent with local tools

### What it does

```
You: what is 1234 * 5678?

Agent:
1234 * 5678 = 7,006,652.

You: what time is it?

Agent:
It is currently 2026-10-07 14:32:10.
```

### How it works

The file is split into numbered sections:

| Section | Code | Purpose |
|---|---|---|
| 1. Client | `client = genai.Client(api_key=...)` | Connects to Gemini. Stops with `RuntimeError` if `GEMINI_API_KEY` is missing |
| 2. Tools | `calculator(expression)`, `get_current_time()` | Plain Python functions the model may call |
| 3. Tool list | `tools = [calculator, get_current_time]` | The functions handed to Gemini |
| 4. Instructions | `SYSTEM_INSTRUCTION` | Tells the model when to use each tool and not to pretend it used one |
| 5. Agent loop | `run_agent()` | Opens a chat session and loops on `input()` until you type `exit` |
| 6. Start | `if __name__ == "__main__"` | Runs `run_agent()` |

**The key idea is automatic function calling.** When you pass ordinary Python functions in `config={"tools": tools}`, the `google-genai` SDK:

1. Reads each function's name, type hints and docstring, and turns them into a tool description the model understands. This is why the docstrings matter: they are what the model reads.
2. Sends your message. If the model replies "call `calculator` with `25 * 17`", the SDK runs that Python function for you.
3. Sends the function's return value back to the model, which then writes the final answer.

All of this happens inside one `chat.send_message(...)` call, so the loop in `run_agent()` never has to deal with tool calls itself.

**Memory:** `client.chats.create(...)` keeps the conversation history, so the agent remembers earlier messages until you exit.

| Function | Details |
|---|---|
| `calculator(expression)` | Evaluates arithmetic with `eval` and no builtins. Returns an error message instead of raising. **Learning example only**: `eval` is not safe for untrusted input |
| `get_current_time()` | Returns local time as `YYYY-MM-DD HH:MM:SS` |
| `run_agent()` | Model `gemini-3.1-flash-lite`. Any error from Gemini (quota, network) is printed and the loop continues |

---

## `agent2.py`: agent with Firecrawl tools over MCP

### What MCP is

The **Model Context Protocol (MCP)** is a standard way for a program (an *MCP server*) to offer tools to any AI agent. Firecrawl publishes an MCP server, so instead of writing search and scrape functions yourself, you start the server and ask it which tools it has.

### How it works

| Part | Code | Purpose |
|---|---|---|
| Model | `ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0)` | Gemini through LangChain. `temperature=0` makes answers more consistent |
| Server settings | `StdioServerParameters(command="npx", args=["firecrawl-mcp"], env={...})` | How to start the Firecrawl MCP server as a child process, passing it `FIRECRAWL_API_KEY` |
| Local tool | `calculator(expression)` | Same as in `agent.py` |
| `run_agent()` (async) | see below | Starts the server, loads its tools and builds the agent |

Steps inside `run_agent()`:

1. `stdio_client(server_params)` runs `npx firecrawl-mcp` and talks to it through stdin/stdout.
2. `ClientSession(...)` and `session.initialize()` perform the MCP handshake.
3. `load_mcp_tools(session)` asks the server for its tools (web search, scrape, crawl, ...) and converts them into LangChain tools.
4. `create_react_agent(model, tools)` builds a LangGraph **ReAct** agent with the calculator plus all Firecrawl tools. ReAct means the model loops: *think → call a tool → read the result → think again*, until it can answer.

### Current limitation

The agent is created but never used. `run_agent()` ends right after `create_react_agent`, so running the script starts the server, loads the tools and exits without printing anything. To make it answer a question, add this inside the `async with` block:

```python
response = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "Find the pricing of Supabase"}]}
)
print(response["messages"][-1].content)
```

The agent has to run inside the `async with` blocks, because the MCP tools only work while the session is open.

---

## Setup

### Requirements

- Python 3.10 or newer (developed with 3.12)
- A **Gemini API key**: https://aistudio.google.com/apikey
- For `agent2.py` only: a **Firecrawl API key** (https://www.firecrawl.dev) and **Node.js**, which provides `npx`

### Install packages

From the repo root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1          # Windows PowerShell
# source venv/bin/activate           # macOS / Linux

pip install google-genai python-dotenv                                         # agent.py
pip install langchain-google-genai langgraph mcp langchain-mcp-adapters        # agent2.py
```

### API keys

Create a `.env` file in `SimpleAgent/` or in the repo root:

```
GEMINI_API_KEY=your-gemini-key-here
FIRECRAWL_API_KEY=your-firecrawl-key-here
```

`load_dotenv()` looks for `.env` in the script's folder first and then in each parent folder, so it does **not** find `AdvancedAgent/.env`. `.env` is ignored by git. Never commit it.

### Run

```powershell
python SimpleAgent/agent.py
python SimpleAgent/agent2.py
```

---

## Troubleshooting

| Message | Meaning | What to do |
|---|---|---|
| `RuntimeError: GEMINI_API_KEY environment variable is not set.` | No `.env` was found | Create `.env` as described above |
| `ModuleNotFoundError: No module named 'mcp'` (or `langchain_mcp_adapters`, `langgraph`) | The `agent2.py` packages aren't installed | Run the second `pip install` line |
| `FileNotFoundError` mentioning `npx` | Node.js isn't installed or isn't on `PATH` | Install Node.js |
| `429 RESOURCE_EXHAUSTED` | Gemini free-tier quota used up | Wait for the reset or change the model name |
| `404 ... model not found` | That Gemini model name was retired | Change the `model=` string to a current model |

---

## Ideas for practice

1. Finish `agent2.py`: add an input loop like `agent.py` that calls `agent.ainvoke(...)`.
2. Replace `eval` in the calculator with a safe parser (e.g. Python's `ast` module, allowing only numbers and arithmetic operators).
3. Add a new tool to `agent.py`, such as a unit converter, and watch Gemini pick it up from the docstring alone.
4. `create_react_agent` is LangGraph's older prebuilt agent. Newer LangChain versions offer `langchain.agents.create_agent` for the same job, so try switching to it.
5. Add a `requirements.txt` to this folder, like the AdvancedAgent has.
