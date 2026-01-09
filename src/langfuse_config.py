"""
Langfuse configuration for LLM observability.
Provides tracing, metrics, and cost tracking for LLM calls.
"""

import os
from functools import wraps
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)

# Check if Langfuse is configured
LANGFUSE_ENABLED = bool(
    os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
)

_langfuse_client = None


def get_langfuse():
    """Get or create Langfuse client."""
    global _langfuse_client

    if not LANGFUSE_ENABLED:
        return None

    if _langfuse_client is None:
        try:
            from langfuse import Langfuse
            _langfuse_client = Langfuse()
            logger.info("Langfuse client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}")
            return None

    return _langfuse_client


def trace_llm_call(
    name: str = "llm-call",
    model: Optional[str] = None,
):
    """
    Decorator to trace LLM calls with Langfuse.

    Args:
        name: Name of the trace
        model: Model name for the generation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            langfuse = get_langfuse()

            if langfuse is None:
                # Langfuse not configured, just run the function
                return func(*args, **kwargs)

            # Create trace
            trace = langfuse.trace(name=name)

            # Create generation span
            generation = trace.generation(
                name=f"{name}-generation",
                model=model or kwargs.get("model", "unknown"),
                input=kwargs.get("messages", args[0] if args else None),
            )

            try:
                result = func(*args, **kwargs)

                # Update generation with output
                if isinstance(result, dict):
                    output = result.get("choices", [{}])[0].get("message", {}).get("content")
                    usage = result.get("usage", {})

                    generation.end(
                        output=output,
                        usage={
                            "input": usage.get("prompt_tokens", 0),
                            "output": usage.get("completion_tokens", 0),
                            "total": usage.get("total_tokens", 0),
                        }
                    )
                else:
                    generation.end(output=str(result))

                return result

            except Exception as e:
                generation.end(
                    output=None,
                    level="ERROR",
                    status_message=str(e),
                )
                raise

        return wrapper
    return decorator


def trace_tool_call(name: str):
    """
    Decorator to trace tool calls with Langfuse.

    Args:
        name: Name of the tool
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            langfuse = get_langfuse()

            if langfuse is None:
                return func(*args, **kwargs)

            trace = langfuse.trace(name=f"tool-{name}")
            span = trace.span(
                name=name,
                input={"args": args, "kwargs": kwargs},
            )

            try:
                result = func(*args, **kwargs)
                span.end(output=result)
                return result
            except Exception as e:
                span.end(
                    output=None,
                    level="ERROR",
                    status_message=str(e),
                )
                raise

        return wrapper
    return decorator


def create_session_trace(session_id: str, user_id: Optional[str] = None):
    """
    Create a trace for a chat session.

    Args:
        session_id: Unique session identifier
        user_id: Optional user identifier

    Returns:
        Trace object or None if Langfuse is not configured
    """
    langfuse = get_langfuse()

    if langfuse is None:
        return None

    return langfuse.trace(
        name="chat-session",
        session_id=session_id,
        user_id=user_id,
    )


def flush():
    """Flush any pending Langfuse events."""
    langfuse = get_langfuse()
    if langfuse:
        langfuse.flush()
