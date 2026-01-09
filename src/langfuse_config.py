"""
Langfuse configuration for LLM observability.
Provides tracing, metrics, and cost tracking for LLM calls.
"""

import os
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


def create_trace(name: str, session_id: str = None, user_input: str = None, metadata: dict = None):
    """
    Create a Langfuse trace for observability.

    Returns a trace object or None if Langfuse is not configured.
    """
    if not LANGFUSE_ENABLED:
        return None

    try:
        from langfuse import get_client
        langfuse = get_client()

        # Use start_as_current_observation for v3 SDK
        trace = langfuse.start_as_current_observation(
            as_type="span",
            name=name,
            input=user_input,
            metadata=metadata or {},
        )

        # Set session_id if provided
        if session_id:
            from langfuse import update_current_trace
            update_current_trace(session_id=session_id)

        return trace
    except Exception as e:
        logger.warning(f"Failed to create Langfuse trace: {e}")
        return None


def create_generation(name: str, model: str, messages: list, model_params: dict = None):
    """
    Create a Langfuse generation span for LLM calls.

    Returns a generation object or None if Langfuse is not configured.
    """
    if not LANGFUSE_ENABLED:
        return None

    try:
        from langfuse import get_client
        langfuse = get_client()

        generation = langfuse.start_as_current_observation(
            as_type="generation",
            name=name,
            model=model,
            input=messages,
            model_parameters=model_params or {},
        )
        return generation
    except Exception as e:
        logger.warning(f"Failed to create Langfuse generation: {e}")
        return None


def create_span(name: str, input_data: dict = None):
    """
    Create a Langfuse span for tool calls.

    Returns a span object or None if Langfuse is not configured.
    """
    if not LANGFUSE_ENABLED:
        return None

    try:
        from langfuse import get_client
        langfuse = get_client()

        span = langfuse.start_as_current_observation(
            as_type="span",
            name=name,
            input=input_data,
        )
        return span
    except Exception as e:
        logger.warning(f"Failed to create Langfuse span: {e}")
        return None


def end_observation(observation, output=None, usage=None, level="DEFAULT", status_message=None):
    """
    End a Langfuse observation (trace, generation, or span).
    """
    if observation is None:
        return

    try:
        if usage:
            observation.update(output=output, usage=usage)
        elif output:
            observation.update(output=output)

        if level == "ERROR" and status_message:
            observation.update(level=level, status_message=status_message)

        observation.end()
    except Exception as e:
        logger.warning(f"Failed to end Langfuse observation: {e}")


def flush():
    """Flush any pending Langfuse events."""
    if not LANGFUSE_ENABLED:
        return

    try:
        from langfuse import get_client
        langfuse = get_client()
        langfuse.flush()
    except Exception as e:
        logger.warning(f"Failed to flush Langfuse: {e}")
