import os
import queue
import threading
from datetime import date

import gradio as gr
from dotenv import load_dotenv

from src.models import ANALYSIS_FAILED
from src.workflow import Workflow
from ui_theme import CSS, FORCE_DARK_JS, THEME

load_dotenv()


def get_owner_key(name: str) -> str | None:
    """Read one of the app owner's API keys: Space secrets when deployed, .env when run locally."""
    return os.getenv(name)


# Max number of queries per day that may use the owner's keys (visitors with their own keys are unlimited)
DEMO_DAILY_LIMIT = int(get_owner_key("DEMO_DAILY_LIMIT") or 3)

# One usage counter shared by every visitor (it resets when the app restarts)
demo_usage = {"date": None, "count": 0, "lock": threading.Lock()}


def demo_runs_left() -> int:
    """How many demo queries are left today."""
    with demo_usage["lock"]:
        if demo_usage["date"] != date.today():
            demo_usage["date"], demo_usage["count"] = date.today(), 0
        return DEMO_DAILY_LIMIT - demo_usage["count"]


def use_demo_run() -> bool:
    """Count one demo query. Returns False if today's limit is already reached."""
    with demo_usage["lock"]:
        if demo_usage["date"] != date.today():
            demo_usage["date"], demo_usage["count"] = date.today(), 0
        if demo_usage["count"] >= DEMO_DAILY_LIMIT:
            return False
        demo_usage["count"] += 1
        return True


def key_status(user_gemini_key: str, user_firecrawl_key: str) -> str:
    """Text for the sidebar that tells the visitor which keys are being used."""
    if user_gemini_key and user_firecrawl_key:
        return "✅ Using your keys. No limit."
    return f"ℹ️ Demo mode: {max(demo_runs_left(), 0)} of {DEMO_DAILY_LIMIT} free searches left today."


def format_company(company) -> str:
    """Turn one researched tool into a markdown card."""
    def cell(value: str) -> str:
        return value.replace("|", "\\|")

    pricing = company.pricing_model or "Unknown"
    open_source = {True: "Yes", False: "No"}.get(company.is_open_source, "Unknown")
    api = {True: "Available", False: "Not available"}.get(company.api_available, "Unknown")

    lines = [f"### {company.name}"]
    if company.website:
        lines.append(f"🌐 [{company.website}]({company.website})")
    lines += [
        "",
        "| 💰 Pricing | 📖 Open source | 🔌 API |",
        "|---|---|---|",
        f"| {cell(pricing)} | {open_source} | {api} |",
        "",
    ]
    if company.description and company.description != ANALYSIS_FAILED:
        lines += [company.description, ""]
    if company.tech_stack:
        lines.append(f"**🛠️ Tech stack:** {', '.join(company.tech_stack[:5])}  ")
    if company.language_support:
        lines.append(f"**💻 Languages:** {', '.join(company.language_support[:5])}  ")
    if company.integration_capabilities:
        lines.append(f"**🔗 Integrations:** {', '.join(company.integration_capabilities[:4])}  ")
    return "\n".join(lines)


def card(markdown: str, css_class: str = "tool-card") -> str:
    """Wrap markdown in a div so it gets the rounded card style from ui_theme.py.

    The blank lines around the markdown make sure it is still rendered as markdown inside the div.
    """
    return f'<div class="{css_class}">\n\n{markdown}\n\n</div>'


def format_result(result) -> str:
    """Turn the whole research result into markdown: the recommendation first, then one card per tool."""
    parts = []
    if result.analysis:
        parts.append(card(f"### 💡 Recommendation\n\n{result.analysis}", "tool-card recommendation"))
    if not result.companies:
        parts.append("⚠️ No tools could be researched. Try a different query, or check your API keys.")
    parts += [card(format_company(company)) for company in result.companies]
    return f"## 📊 Results for `{result.query}`\n\n" + "\n\n".join(parts)


def research(query: str, user_gemini_key: str, user_firecrawl_key: str):
    """Run the agent and stream progress to the page.

    This is a generator: every `yield` updates (progress, results, key status, button) in the browser.
    """
    query = query.strip()
    using_own_keys = bool(user_gemini_key and user_firecrawl_key)
    button_busy = gr.update(value="Researching...", interactive=False)
    button_ready = gr.update(value="Research", interactive=True)

    if not query:
        yield "⚠️ Type a topic first.", gr.update(), key_status(user_gemini_key, user_firecrawl_key), button_ready
        return

    gemini_key = user_gemini_key or get_owner_key("GEMINI_API_KEY")
    firecrawl_key = user_firecrawl_key or get_owner_key("FIRECRAWL_API_KEY")

    if not gemini_key or not firecrawl_key:
        yield "❌ No API keys available. Enter your own keys in the sidebar.", gr.update(), key_status(user_gemini_key, user_firecrawl_key), button_ready
        return
    if not using_own_keys and not use_demo_run():
        yield (
            "⚠️ Today's free demo searches are used up. Enter your own API keys in the sidebar to keep going.",
            gr.update(), key_status(user_gemini_key, user_firecrawl_key), button_ready,
        )
        return

    # The workflow runs in a background thread and reports each finished step through this queue,
    # so this function can keep yielding progress to the page while the agent works.
    events = queue.Queue()

    def on_step(step_name, state):
        """Turn each finished workflow step into progress lines."""
        if step_name == "extracted_tools":
            if state.extracted_tools:
                events.put(("log", f"✅ Found tools: {', '.join(state.extracted_tools[:5])}"))
            else:
                events.put(("log", "⚠️ No tools found in articles, falling back to a direct search"))
            events.put(("label", "Reading each tool's website..."))
        elif step_name == "research":
            events.put(("log", f"✅ Researched {len(state.companies)} tools"))
            events.put(("label", "Writing recommendation..."))

    def run_workflow():
        try:
            workflow = Workflow(gemini_api_key=gemini_key, firecrawl_api_key=firecrawl_key)
            events.put(("done", workflow.run(query, on_step=on_step)))
        except Exception as e:
            events.put(("error", e))

    threading.Thread(target=run_workflow, daemon=True).start()

    label, log = "Searching for articles and extracting tools...", []

    def progress() -> str:
        return "\n\n".join([f"⏳ **{label}**", *log])

    yield progress(), "", key_status(user_gemini_key, user_firecrawl_key), button_busy

    while True:
        kind, value = events.get()
        if kind == "log":
            log.append(value)
        elif kind == "label":
            label = value
        elif kind == "done":
            yield "\n\n".join(["✅ **Done!**", *log]), format_result(value), key_status(user_gemini_key, user_firecrawl_key), button_ready
            return
        elif kind == "error":
            yield f"❌ **The agent failed:** {value}", "", key_status(user_gemini_key, user_firecrawl_key), button_ready
            return
        yield progress(), gr.update(), gr.update(), gr.update()


with gr.Blocks(title="Developer Tools Research Agent") as demo:
    # ---------- Sidebar: optional visitor API keys ----------
    with gr.Sidebar(elem_classes="key-sidebar"):
        gr.Markdown(
            "## 🔑 API keys (optional)\n"
            "Use your own free keys for unlimited searches. "
            "They are only used for your request and are never stored."
        )
        user_gemini_key = gr.Textbox(
            label="Gemini API key", type="password", info="Get one at https://aistudio.google.com/apikey"
        )
        user_firecrawl_key = gr.Textbox(
            label="Firecrawl API key", type="password", info="Get one at https://www.firecrawl.dev"
        )
        key_status_box = gr.Markdown(elem_classes="key-status")

    # ---------- Main page ----------
    gr.HTML(
        '<div class="hero">'
        '<span class="hero-badge"><span class="dot"></span>agent online · langgraph + gemini + firecrawl</span>'
        '<h1><span class="prompt">&gt;_</span> Developer Tools Research Agent</h1>'
        "<p>Type a topic and the agent searches the web, finds the most relevant developer tools, "
        "reads their websites and recommends the best option.</p>"
        "</div>"
    )
    with gr.Row(elem_classes="search-bar"):
        query = gr.Textbox(
            label="What kind of developer tool are you looking for?",
            placeholder="e.g. vector databases, CI/CD tools, headless CMS",
            scale=5,
        )
        research_button = gr.Button("Research", variant="primary", scale=1)

    progress_box = gr.Markdown("$ waiting for a query...", elem_classes="terminal")
    results_box = gr.Markdown(elem_classes="results")

    gr.Markdown(
        "Built with LangGraph, Google Gemini and Firecrawl · [Source code](https://github.com/mu-az88/AI-Agent)",
        elem_classes="app-footer",
    )

    # ---------- Events ----------
    key_inputs = [user_gemini_key, user_firecrawl_key]
    research_outputs = [progress_box, results_box, key_status_box, research_button]

    # Pressing Enter in the search box does the same as clicking the button
    gr.on(
        triggers=[research_button.click, query.submit],
        fn=research,
        inputs=[query, *key_inputs],
        outputs=research_outputs,
    )
    # Keep the sidebar status up to date when the page opens and when keys are typed
    gr.on(
        triggers=[demo.load, user_gemini_key.change, user_firecrawl_key.change],
        fn=key_status,
        inputs=key_inputs,
        outputs=key_status_box,
    )


if __name__ == "__main__":
    demo.launch(theme=THEME, css=CSS, js=FORCE_DARK_JS)
