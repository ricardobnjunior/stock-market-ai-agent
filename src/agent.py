"""
AI Agent that uses OpenRouter for LLM and tools for stock market data.
Supports streaming responses and status callbacks.
"""

import os
import json
import time
import uuid
import requests
from pathlib import Path
from typing import Optional, Generator, Callable
from dotenv import load_dotenv

# Load .env from the same directory as this file
_current_dir = Path(__file__).parent
load_dotenv(_current_dir / ".env")

from tools import TOOLS, TOOL_FUNCTIONS
from logging_config import setup_logging, get_logger, metrics
from rate_limiter import llm_limiter, rate_limited, RateLimitExceeded
from validation import sanitize_user_input
from langfuse_config import (
    LANGFUSE_ENABLED,
    create_trace,
    create_generation,
    create_span,
    end_generation,
    end_span,
    end_trace,
    flush,
)

# Setup logging
logger = get_logger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"

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

# Tool descriptions for user feedback
TOOL_DESCRIPTIONS = {
    "get_current_price": "Fetching current price",
    "get_price_yesterday": "Fetching yesterday's price",
    "get_price_change": "Calculating price change",
    "get_average_price": "Calculating average price",
    "get_historical_data": "Fetching historical data",
    "get_chart_data": "Preparing chart data",
    "compare_stocks": "Comparing stocks",
    "calculate": "Performing calculation",
}


def get_api_key() -> str:
    """Get OpenRouter API key from environment or Streamlit secrets."""
    # Try environment variable first (works locally and in Docker)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    # Try Streamlit secrets as fallback (for Streamlit Cloud deployment)
    try:
        import streamlit as st
        api_key = st.secrets.get("OPENROUTER_API_KEY", None)
        if api_key:
            return api_key
    except Exception:
        pass

    raise ValueError(
        "OPENROUTER_API_KEY not found. "
        "Set it in .env file or Streamlit Cloud secrets."
    )


@rate_limited(llm_limiter)
def call_llm(
    messages: list,
    tools: Optional[list] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    stream: bool = False,
    trace: Optional[object] = None,
) -> dict | requests.Response:
    """Call OpenRouter API."""
    api_key = get_api_key()
    start_time = time.time()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://everme-stock-agent.com",
        "X-Title": "EverMe Stock Agent",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    if tools:
        payload["tools"] = [
            {"type": "function", "function": tool} for tool in tools
        ]
        payload["tool_choice"] = "auto"

    logger.info(f"Calling LLM (model={model}, stream={stream})")

    # Create Langfuse generation if trace provided and not streaming
    generation = None
    if trace and not stream:
        generation = create_generation(
            trace=trace,
            name="llm-call",
            model=model,
            messages=messages,
            model_params={"temperature": temperature, "max_tokens": max_tokens},
        )

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=60,
        stream=stream,
    )
    response.raise_for_status()

    elapsed = (time.time() - start_time) * 1000
    logger.info(f"LLM response received in {elapsed:.0f}ms")

    if stream:
        return response

    result = response.json()

    # Update Langfuse generation with output and usage
    if generation:
        output = result.get("choices", [{}])[0].get("message", {})
        usage_data = result.get("usage", {})
        end_generation(
            generation,
            output=output,
            usage={
                "input": usage_data.get("prompt_tokens", 0),
                "output": usage_data.get("completion_tokens", 0),
                "total": usage_data.get("total_tokens", 0),
            },
        )

    return result


def execute_tool(tool_name: str, arguments: dict, trace: Optional[object] = None) -> str:
    """Execute a tool and return the result as a string."""
    start_time = time.time()

    if tool_name not in TOOL_FUNCTIONS:
        logger.warning(f"Unknown tool requested: {tool_name}")
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    logger.info(f"Executing tool: {tool_name} with args: {arguments}")

    # Create Langfuse span for tool execution
    span = None
    if trace:
        span = create_span(trace=trace, name=f"tool-{tool_name}", input_data=arguments)

    func = TOOL_FUNCTIONS[tool_name]
    result = func(**arguments)

    elapsed = (time.time() - start_time) * 1000
    success = "error" not in result

    # Record metrics
    metrics.record_tool_call(tool_name, success, elapsed)

    # End Langfuse span
    if span:
        end_span(span, output=result, level="DEFAULT" if success else "ERROR")

    if success:
        logger.info(f"Tool {tool_name} completed in {elapsed:.0f}ms")
    else:
        logger.warning(f"Tool {tool_name} failed: {result.get('error')}")
        metrics.record_error("tool_error", f"{tool_name}: {result.get('error')}")

    return json.dumps(result)


def parse_sse_stream(response: requests.Response) -> Generator[str, None, None]:
    """Parse SSE stream and yield content chunks."""
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


def run_agent_with_streaming(
    user_message: str,
    conversation_history: list,
    on_status: Optional[Callable[[str, str], None]] = None,
    session_id: Optional[str] = None,
) -> Generator[str | dict, None, None]:
    """
    Run the agent with streaming support.

    Yields:
        - dict with "status" key for status updates
        - str chunks for streaming response
        - dict with "done" key when complete

    Args:
        user_message: The user's input
        conversation_history: List of previous messages
        on_status: Optional callback for status updates (label, state)
        session_id: Optional session ID for Langfuse tracing
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # Create Langfuse trace for this conversation turn
    trace = None
    if LANGFUSE_ENABLED:
        trace = create_trace(
            name="agent-turn",
            session_id=session_id or str(uuid.uuid4()),
            user_input=user_message,
            metadata={"history_length": len(conversation_history)},
        )

    # Status: Analyzing
    yield {"status": "Analyzing your question...", "state": "running"}

    # First call - check if tools are needed (non-streaming to get tool calls)
    response = call_llm(messages, tools=TOOLS, stream=False, trace=trace)
    assistant_message = response["choices"][0]["message"]

    # Check if the model wants to use tools
    if assistant_message.get("tool_calls"):
        messages.append(assistant_message)

        for tool_call in assistant_message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            # Get ticker/expression for better feedback
            ticker = arguments.get("ticker", arguments.get("expression", ""))
            description = TOOL_DESCRIPTIONS.get(tool_name, "Processing")
            status_msg = f"{description}: {ticker}" if ticker else description

            yield {"status": status_msg, "state": "running"}

            # Execute tool
            tool_result = execute_tool(tool_name, arguments, trace=trace)

            # Show tool result
            yield {"tool_call": tool_name, "args": arguments, "result": json.loads(tool_result)}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": tool_result,
            })

        # Status: Generating response
        yield {"status": "Generating response...", "state": "running"}

        # Second call with streaming
        stream_response = call_llm(messages, tools=TOOLS, stream=True, trace=trace)

        full_response = ""
        for chunk in parse_sse_stream(stream_response):
            full_response += chunk
            yield chunk

    else:
        # No tools needed - stream directly
        content = assistant_message.get("content", "")
        if content:
            # Already have the response, yield it
            yield {"status": "Generating response...", "state": "running"}
            for char in content:
                yield char
            full_response = content
        else:
            # Stream the response
            yield {"status": "Generating response...", "state": "running"}
            stream_response = call_llm(messages, stream=True, trace=trace)
            full_response = ""
            for chunk in parse_sse_stream(stream_response):
                full_response += chunk
                yield chunk

    # End Langfuse trace with output
    end_trace(trace, output=full_response)

    # Flush Langfuse events
    flush()

    # Update conversation history
    updated_history = conversation_history.copy()
    updated_history.append({"role": "user", "content": user_message})
    updated_history.append({"role": "assistant", "content": full_response})

    yield {"done": True, "history": updated_history}


# Keep the old function for compatibility
def run_agent(user_message: str, conversation_history: list) -> tuple[str, list]:
    """Run the agent without streaming (legacy)."""
    full_response = ""
    final_history = conversation_history

    for item in run_agent_with_streaming(user_message, conversation_history):
        if isinstance(item, dict):
            if item.get("done"):
                final_history = item["history"]
        else:
            full_response += item

    return full_response, final_history
