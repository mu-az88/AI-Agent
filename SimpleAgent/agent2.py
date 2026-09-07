from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()


# Initialize the Gemini model via LangChain using the AI Studio API key
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    temperature=0,
    google_api_key=os.getenv("GEMINI_API_KEY")
)


# Initialize the Firecrawl MCP server
server_params = StdioServerParameters(
    command="npx",
    env={
        "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY"),
    },
    args=["firecrawl-mcp"]
)


# Define a calculator capability
def calculator(expression: str) -> str:
    """
    Calculate a mathematical expression.

    Args:
        expression: A mathematical expression such as
                    "25 * 17" or "100 / 4 + 7".

    Returns:
        The result of the calculation.
    """
    try:
        # For a learning example only.
        # Do NOT use eval like this with untrusted production input.
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Could not calculate expression: {e}"


async def run_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Load Firecrawl tools from the MCP server
            firecrawl_tools = await load_mcp_tools(session)

            # Combine local tools with Firecrawl tools
            tools = [calculator] + firecrawl_tools

            # Create the agent with all available tools
            agent = create_react_agent(model, tools)


if __name__ == "__main__":
    asyncio.run(run_agent())
