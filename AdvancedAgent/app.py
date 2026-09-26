import os
import threading
from datetime import date

import streamlit as st
from dotenv import load_dotenv

from src.models import ANALYSIS_FAILED
from src.workflow import Workflow

load_dotenv()

st.set_page_config(page_title="Developer Tools Research Agent", page_icon="🔎", layout="wide")


def get_owner_key(name: str) -> str | None:
    """Read one of the app owner's API keys: Streamlit secrets when deployed, .env when run locally."""
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name)


# Max number of queries per day that may use the owner's keys (visitors with their own keys are unlimited)
DEMO_DAILY_LIMIT = int(get_owner_key("DEMO_DAILY_LIMIT") or 3)


@st.cache_resource
def demo_usage() -> dict:
    """One usage counter shared by every visitor (it resets when the app restarts)."""
    return {"date": None, "count": 0, "lock": threading.Lock()}


def demo_runs_left() -> int:
    """How many demo queries are left today."""
    usage = demo_usage()
    with usage["lock"]:
        if usage["date"] != date.today():
            usage["date"], usage["count"] = date.today(), 0
        return DEMO_DAILY_LIMIT - usage["count"]


def use_demo_run() -> bool:
    """Count one demo query. Returns False if today's limit is already reached."""
    usage = demo_usage()
    with usage["lock"]:
        if usage["date"] != date.today():
            usage["date"], usage["count"] = date.today(), 0
        if usage["count"] >= DEMO_DAILY_LIMIT:
            return False
        usage["count"] += 1
        return True


def show_company(company) -> None:
    """Draw one researched tool as a card."""
    with st.container(border=True):
        st.subheader(company.name)
        if company.website:
            st.markdown(f"🌐 [{company.website}]({company.website})")

        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Pricing", company.pricing_model or "Unknown")
        col2.metric("📖 Open source", {True: "Yes", False: "No"}.get(company.is_open_source, "Unknown"))
        col3.metric("🔌 API", {True: "Available", False: "Not available"}.get(company.api_available, "Unknown"))

        if company.description and company.description != ANALYSIS_FAILED:
            st.write(company.description)
        if company.tech_stack:
            st.markdown(f"**🛠️ Tech stack:** {', '.join(company.tech_stack[:5])}")
        if company.language_support:
            st.markdown(f"**💻 Languages:** {', '.join(company.language_support[:5])}")
        if company.integration_capabilities:
            st.markdown(f"**🔗 Integrations:** {', '.join(company.integration_capabilities[:4])}")


# ---------- Sidebar: optional visitor API keys ----------
with st.sidebar:
    st.header("🔑 API keys (optional)")
    st.write(
        "Use your own free keys for unlimited searches. "
        "They are only used for your request and are never stored."
    )
    user_gemini_key = st.text_input("Gemini API key", type="password", help="Get one at https://aistudio.google.com/apikey")
    user_firecrawl_key = st.text_input("Firecrawl API key", type="password", help="Get one at https://www.firecrawl.dev")

    using_own_keys = bool(user_gemini_key and user_firecrawl_key)
    # Filled in at the end of the page, so the count already includes a search made on this run
    key_status = st.empty()

# ---------- Main page ----------
st.title("🔎 Developer Tools Research Agent")
st.write(
    "Type a topic and the agent searches the web, finds the most relevant developer tools, "
    "reads their websites and recommends the best option."
)

with st.form("query_form"):
    query = st.text_input("What kind of developer tool are you looking for?", placeholder="e.g. vector databases, CI/CD tools, headless CMS")
    submitted = st.form_submit_button("Research", type="primary")

if submitted and query.strip():
    gemini_key = user_gemini_key or get_owner_key("GEMINI_API_KEY")
    firecrawl_key = user_firecrawl_key or get_owner_key("FIRECRAWL_API_KEY")

    if not gemini_key or not firecrawl_key:
        st.error("No API keys available. Enter your own keys in the sidebar.")
    elif not using_own_keys and not use_demo_run():
        st.warning("Today's free demo searches are used up. Enter your own API keys in the sidebar to keep going.")
    else:
        with st.status("Searching for articles and extracting tools...", expanded=True) as status:

            def on_step(step_name, state):
                """Show progress in the status box after each workflow step."""
                if step_name == "extracted_tools":
                    if state.extracted_tools:
                        status.write(f"✅ Found tools: {', '.join(state.extracted_tools[:5])}")
                    else:
                        status.write("⚠️ No tools found in articles, falling back to a direct search")
                    status.update(label="Reading each tool's website...")
                elif step_name == "research":
                    status.write(f"✅ Researched {len(state.companies)} tools")
                    status.update(label="Writing recommendation...")

            try:
                workflow = Workflow(gemini_api_key=gemini_key, firecrawl_api_key=firecrawl_key)
                st.session_state.result = workflow.run(query.strip(), on_step=on_step)
                status.update(label="Done!", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Something went wrong", state="error")
                st.error(f"The agent failed: {e}")

# Results are kept in session_state so they stay visible when the page reruns
result = st.session_state.get("result")
if result:
    st.header(f"📊 Results for: {result.query}")

    if result.analysis:
        with st.container(border=True):
            st.subheader("💡 Recommendation")
            st.markdown(result.analysis)

    if not result.companies:
        st.warning("No tools could be researched. Try a different query, or check your API keys.")
    for company in result.companies:
        show_company(company)

if using_own_keys:
    key_status.success("Using your keys. No limit.")
else:
    key_status.info(f"Demo mode: {max(demo_runs_left(), 0)} of {DEMO_DAILY_LIMIT} free searches left today.")

st.caption("Built with LangGraph, Google Gemini and Firecrawl · [Source code](https://github.com/mu-az88/AI-Agent)")
