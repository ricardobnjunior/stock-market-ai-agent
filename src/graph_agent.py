"""
LangGraph-based AI Agent for stock market data.
Uses a state graph for structured tool calling and conversation flow.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Annotated, TypedDict, Literal, Generator, Optional
from dotenv import load_dotenv

# Load .env from the same directory as this file
_current_dir = Path(__file__).parent
load_dotenv(_current_dir / ".env")

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from tools import (
    get_current_price,
    get_price_yesterday,
    get_price_change,
    get_average_price,
    get_historical_data,
    get_chart_data,
    compare_stocks,
    calculate,
)
from logging_config import get_logger, metrics
from langfuse_config import (
    LANGFUSE_ENABLED,
    create_trace,
    end_trace,
    flush,
)

logger = get_logger(__name__)

# System prompt
SYSTEM_PROMPT = """You are a helpful financial assistant that provides real-time stock market information and performs calculations.

You have access to tools that can:
- Get current prices for stocks and cryptocurrencies
- Get yesterday's closing prices
- Calculate price changes and percentage changes
- Calculate average prices over a period
- Get historical data
- Compare multiple stocks (use compare_stocks when user mentions 2+ tickers)
- Show price charts (use get_chart_data when user asks for charts/graphs)
- Perform mathematical calculations

IMPORTANT: When user wants to compare multiple stocks, use compare_stocks tool with all tickers at once. Do NOT call get_current_price multiple times.

When users ask about stocks or crypto, use the appropriate tool to fetch real data.
Common ticker mappings: Bitcoin=BTC-USD, Tesla=TSLA, Apple=AAPL, Google=GOOGL, Amazon=AMZN

Always be helpful and provide a clear text summary after showing data.
Keep responses concise but informative."""


# Define LangChain tools wrapping existing functions
@tool
def tool_get_current_price(ticker: str) -> str:
    """Get current price for a stock or cryptocurrency.

    Args:
        ticker: Stock symbol or common name (e.g., 'AAPL', 'Tesla', 'Bitcoin', 'BTC-USD')
    """
    result = get_current_price(ticker)
    return json.dumps(result)


@tool
def tool_get_price_yesterday(ticker: str) -> str:
    """Get yesterday's closing price for a stock or cryptocurrency.

    Args:
        ticker: Stock symbol or common name
    """
    result = get_price_yesterday(ticker)
    return json.dumps(result)


@tool
def tool_get_price_change(ticker: str) -> str:
    """Get price change since yesterday for a stock or cryptocurrency.

    Args:
        ticker: Stock symbol or common name
    """
    result = get_price_change(ticker)
    return json.dumps(result)


@tool
def tool_get_average_price(ticker: str, days: int = 7) -> str:
    """Get average price over a number of days.

    Args:
        ticker: Stock symbol or common name
        days: Number of days for average calculation (default: 7)
    """
    result = get_average_price(ticker, days)
    return json.dumps(result)


@tool
def tool_get_historical_data(ticker: str, period: str = "1mo") -> str:
    """Get historical price data for a stock or cryptocurrency.

    Args:
        ticker: Stock symbol or common name
        period: Time period - '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'
    """
    result = get_historical_data(ticker, period)
    return json.dumps(result)


@tool
def tool_get_chart_data(ticker: str, period: str = "1mo") -> str:
    """Get data formatted for chart visualization.

    Args:
        ticker: Stock symbol or common name
        period: Time period for chart data
    """
    result = get_chart_data(ticker, period)
    return json.dumps(result)


@tool
def tool_compare_stocks(tickers: list[str]) -> str:
    """Compare multiple stocks side by side. ALWAYS use this when comparing 2 or more stocks.

    Args:
        tickers: List of stock symbols or names to compare (max 5)
    """
    result = compare_stocks(tickers)
    return json.dumps(result)


@tool
def tool_calculate(expression: str) -> str:
    """Perform mathematical calculations.

    Args:
        expression: Math expression to evaluate (e.g., '100 * 1.05', '(500-450)/450*100')
    """
    result = calculate(expression)
    return json.dumps(result)


# All tools
LANGGRAPH_TOOLS = [
    tool_get_current_price,
    tool_get_price_yesterday,
    tool_get_price_change,
    tool_get_average_price,
    tool_get_historical_data,
    tool_get_chart_data,
    tool_compare_stocks,
    tool_calculate,
]

# Tool descriptions for UI feedback
TOOL_DESCRIPTIONS = {
    "tool_get_current_price": "Fetching current price",
    "tool_get_price_yesterday": "Fetching yesterday's price",
    "tool_get_price_change": "Calculating price change",
    "tool_get_average_price": "Calculating average price",
    "tool_get_historical_data": "Fetching historical data",
    "tool_get_chart_data": "Preparing chart data",
    "tool_compare_stocks": "Comparing stocks",
    "tool_calculate": "Performing calculation",
}


# State definition
class AgentState(TypedDict):
    """State schema for the agent graph."""
    messages: Annotated[list, add_messages]
    tool_results: list[dict]  # Store tool results for UI


def get_llm():
    """Get the LLM instance configured for OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment")

    return ChatOpenAI(
        model="openai/gpt-4o-mini",
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.7,
        max_tokens=1024,
        default_headers={
            "HTTP-Referer": "https://everme-stock-agent.com",
            "X-Title": "EverMe Stock Agent",
        },
    )


def create_agent_graph():
    """Create the LangGraph agent graph."""

    llm = get_llm()
    llm_with_tools = llm.bind_tools(LANGGRAPH_TOOLS)

    # Agent node - calls the LLM
    def agent_node(state: AgentState) -> dict:
        """Call the LLM with current messages."""
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # Tool node - executes tools
    tool_node = ToolNode(LANGGRAPH_TOOLS)

    # Custom tool node to capture results for UI
    def tool_node_with_capture(state: AgentState) -> dict:
        """Execute tools and capture results for UI display."""
        result = tool_node.invoke(state)

        # Extract tool results for UI
        tool_results = state.get("tool_results", [])
        for msg in result.get("messages", []):
            if isinstance(msg, ToolMessage):
                try:
                    parsed = json.loads(msg.content)
                    tool_results.append({
                        "name": msg.name,
                        "result": parsed,
                    })
                except json.JSONDecodeError:
                    tool_results.append({
                        "name": msg.name,
                        "result": {"raw": msg.content},
                    })

        return {
            "messages": result.get("messages", []),
            "tool_results": tool_results,
        }

    # Router function - decide next step
    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        """Determine if we should continue to tools or end."""
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"

    # Build the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node_with_capture)

    # Set entry point
    graph.set_entry_point("agent")

    # Add conditional edges
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )

    # After tools, go back to agent
    graph.add_edge("tools", "agent")

    # Compile the graph
    return graph.compile()


# Global graph instance
_graph = None


def get_graph():
    """Get or create the agent graph."""
    global _graph
    if _graph is None:
        _graph = create_agent_graph()
    return _graph


def run_graph_agent(
    user_message: str,
    conversation_history: list,
    session_id: Optional[str] = None,
) -> Generator[str | dict, None, None]:
    """
    Run the LangGraph agent with streaming support.

    Yields:
        - dict with "status" key for status updates
        - dict with "tool_call" key for tool results
        - str chunks for streaming response
        - dict with "done" key when complete
    """
    # Create Langfuse trace
    trace = None
    if LANGFUSE_ENABLED:
        trace = create_trace(
            name="langgraph-agent",
            session_id=session_id or str(uuid.uuid4()),
            user_input=user_message,
            metadata={"history_length": len(conversation_history)},
        )

    # Build messages
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Add conversation history
    for msg in conversation_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # Add current user message
    messages.append(HumanMessage(content=user_message))

    # Initial state
    state = {
        "messages": messages,
        "tool_results": [],
    }

    yield {"status": "Analyzing your question...", "state": "running"}

    try:
        graph = get_graph()

        # Run the graph
        final_state = None
        for event in graph.stream(state, stream_mode="updates"):
            # Process each node's output
            for node_name, node_output in event.items():
                if node_name == "tools":
                    # Yield tool results for UI
                    for tool_result in node_output.get("tool_results", []):
                        tool_name = tool_result.get("name", "")
                        description = TOOL_DESCRIPTIONS.get(tool_name, "Processing")

                        yield {"status": description, "state": "running"}
                        yield {
                            "tool_call": tool_name,
                            "args": {},
                            "result": tool_result.get("result", {}),
                        }

                        # Record metrics
                        metrics.record_tool_call(
                            tool_name,
                            "error" not in tool_result.get("result", {}),
                            0,
                        )

                elif node_name == "agent":
                    # Check if this is the final response
                    new_messages = node_output.get("messages", [])
                    if new_messages:
                        last_msg = new_messages[-1]
                        if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
                            yield {"status": "Generating response...", "state": "running"}

            final_state = node_output

        # Get the final response
        if final_state and "messages" in final_state:
            all_messages = final_state["messages"]
            # Find the last AI message without tool calls
            for msg in reversed(all_messages):
                if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                    response_text = msg.content
                    # Stream the response character by character for UI effect
                    for char in response_text:
                        yield char
                    break
            else:
                response_text = ""
        else:
            response_text = "I apologize, but I couldn't generate a response."
            yield response_text

        # End Langfuse trace
        end_trace(trace, output=response_text)
        flush()

        # Update conversation history
        updated_history = conversation_history.copy()
        updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": response_text})

        yield {"done": True, "history": updated_history}

    except Exception as e:
        logger.error(f"Graph agent error: {e}")
        error_msg = f"Sorry, an error occurred: {str(e)}"
        yield error_msg
        yield {"done": True, "history": conversation_history}


# Legacy function for compatibility
def run_agent_with_streaming(
    user_message: str,
    conversation_history: list,
    on_status=None,
    session_id: Optional[str] = None,
) -> Generator[str | dict, None, None]:
    """Wrapper for backward compatibility."""
    yield from run_graph_agent(user_message, conversation_history, session_id)
