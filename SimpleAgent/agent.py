import os
from datetime import datetime
from google import genai

from dotenv import load_dotenv
load_dotenv()


# ============================================================
# 1. Create the Gemini client
# ============================================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set."
    )

client = genai.Client(api_key=api_key)


# ============================================================
# 2. Define the tools our agent can use
# ============================================================

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


def get_current_time() -> str:
    """
    Get the current local date and time.

    Returns:
        Current date and time as a string.
    """

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# 3. Tell Gemini which tools are available
# ============================================================

tools = [
    calculator,
    get_current_time,
]


# ============================================================
# 4. Create the agent
# ============================================================

SYSTEM_INSTRUCTION = """
You are a helpful AI agent.

You have access to tools.

Use the calculator when the user asks you to perform
a calculation that would benefit from exact computation.

Use get_current_time when the user asks for the current
date or time.

Do not pretend that you used a tool if you did not.
Explain the result clearly after using a tool.
"""


# ============================================================
# 5. Agent loop
# ============================================================

def run_agent():
    """Start a chat in the terminal. Gemini decides by itself when to call the tools above."""

    print("=================================")
    print("      Mini AI Agent")
    print("=================================")
    print("Type 'exit' to quit.\n")

    # We use Gemini's chat interface so the agent
    # remembers previous messages in this session.
    chat = client.chats.create(
        model="gemini-3.1-flash-lite",
        config={
            "system_instruction": SYSTEM_INSTRUCTION,
            "tools": tools,
        },
    )

    while True:

        user_input = input("You: ")

        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        try:

            response = chat.send_message(user_input)

            print("\nAgent:")
            print(response.text)
            print()

        except Exception as e:

            print("\nAgent error:")
            print(e)
            print()


# ============================================================
# 6. Start the agent
# ============================================================

if __name__ == "__main__":
    run_agent()

    