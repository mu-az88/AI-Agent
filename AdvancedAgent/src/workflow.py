import os
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.models import ResearchState, CompanyInfo, CompanyAnalysis, ANALYSIS_FAILED
from src.firecrawl import FirecrawlService
from src.prompts import DeveloperToolsPrompts

class Workflow:
    """Orchestrates the full research pipeline: extract tools → research each tool → analyze → recommend."""

    def __init__(self):
        """Set up the web scraper, the Gemini model, the prompts, and the workflow graph."""
        self.firecrawl = FirecrawlService()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            google_api_key=os.getenv("GEMINI_API_KEY"),
                    )
        self.prompt = DeveloperToolsPrompts()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Assemble and compile the LangGraph state machine."""
        graph = StateGraph(ResearchState)
        graph.add_node("extracted_tools", self._extract_tool_step)
        graph.add_node("research", self._research_step)
        graph.add_node("analysis", self._analyze_step)
        graph.set_entry_point("extracted_tools")
        graph.add_edge("extracted_tools", "research")
        graph.add_edge("research", "analysis")
        graph.add_edge("analysis", END)
        return graph.compile()

    def _extract_tool_step(self, state: ResearchState) -> Dict[str, Any]:
        """Search for articles about the query and use the LLM to pull out relevant tool names."""
        print(f"finding articles about {state.query}")

        article_query = f"{state.query} tools comparison best alternatives"
        search_results = self.firecrawl.search_companies(article_query, num_results=3)

        # Scrape each result and accumulate the markdown text
        all_content = ""
        for result in search_results:
            url = result.get("url", "")
            scraped = self.firecrawl.scrape_company_pages(url)
            if scraped:
                all_content += scraped.markdown[:1500] + "\n\n"

        messages = [
            SystemMessage(content=self.prompt.TOOL_EXTRACTION_SYSTEM),
            HumanMessage(content=self.prompt.tool_extraction_user(state.query, all_content))
        ]
        try:
            response = self.llm.invoke(messages)
            # Split the response into individual tool names, one per line
            tool_names = [
                name.strip()
                for name in response.text.strip().split("\n")
                if name.strip()
            ]
            print(f"Extracted Tools: {', '.join(tool_names[:5])}")
            return {"extracted_tools": tool_names}
        except Exception as e:
            print(e)
            return {"extracted_tools": []}

    def _analyze_company_content(self, company_name: str, content: str) -> CompanyAnalysis:
        """Ask the LLM to extract structured analysis (pricing, stack, API, etc.) from scraped content."""
        structured_llm = self.llm.with_structured_output(CompanyAnalysis)

        messages = [
            SystemMessage(content=self.prompt.TOOL_ANALYSIS_SYSTEM),
            HumanMessage(content=self.prompt.tool_analysis_user(company_name, content))
        ]
        try:
            analysis = structured_llm.invoke(messages)
            return analysis
        except Exception as e:
            print(e)
            # Return a safe default so the pipeline can continue on failure
            return CompanyAnalysis(
                pricing_model="Unknown",
                is_open_source=None,
                tech_stack=[],
                description=ANALYSIS_FAILED,
                api_available=None,
                language_support=[],
                integration_capabilities=[]
            )

    def _research_step(self, state: ResearchState) -> Dict[str, Any]:
        """For each extracted tool, scrape its website and run analysis. Falls back to a direct search if no tools were extracted."""
        extracted_tools = state.extracted_tools

        if not extracted_tools:
            print("No extracted tools found, falling back to direct search")
            search_results = self.firecrawl.search_companies(state.query, num_results=4)
            tool_names = [
                result.get("title") or result.get("url") or "Unknown"
                for result in search_results
            ]
        else:
            tool_names = extracted_tools[:4]

        print(f"Researching specific tools: {', '.join(tool_names)}")

        companies = []
        for tool_name in tool_names:
            # Find the tool's official page
            tool_search_results = self.firecrawl.search_companies(tool_name + " official site", num_results=1)

            if tool_search_results:
                result = tool_search_results[0]
                url = result.get("url", "")

                company = CompanyInfo(
                    name=tool_name,
                    description=result.get("markdown") or result.get("description", ""),
                    website=url,
                    tech_stack=[],
                    competitors=[]
                )

                # Scrape the page and run structured analysis on its content
                scraped = self.firecrawl.scrape_company_pages(url)
                if scraped:
                    content = scraped.markdown
                    analysis = self._analyze_company_content(company.name, content)
                    company.pricing_model = analysis.pricing_model
                    company.is_open_source = analysis.is_open_source
                    company.description = analysis.description
                    company.tech_stack = analysis.tech_stack
                    company.api_available = analysis.api_available
                    company.language_support = analysis.language_support
                    company.integration_capabilities = analysis.integration_capabilities

                companies.append(company)

        return {"companies": companies}

    def _analyze_step(self, state: ResearchState) -> Dict[str, Any]:
        """Generate a final recommendation summary from all researched companies."""
        print("Generating recommendations...")

        company_data = ", ".join([
            company.model_dump_json() for company in state.companies
        ])

        messages = [
            SystemMessage(content=self.prompt.RECOMMENDATIONS_SYSTEM),
            HumanMessage(content=self.prompt.recommendations_user(state.query, company_data))
        ]

        response = self.llm.invoke(messages)
        return {"analysis": response.text}

    def run(self, query: str) -> ResearchState:
        """Entry point — runs the full pipeline and returns the final state."""
        initial_state = ResearchState(query=query)
        final_state = self.workflow.invoke(initial_state)
        return ResearchState(**final_state)
