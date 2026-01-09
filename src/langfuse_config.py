"""
Langfuse configuration for LLM observability.
Provides tracing, metrics, and cost tracking for LLM calls.

This integration is optional and gracefully handles errors.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Check if Langfuse is configured
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_ENABLED = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

_langfuse_client = None


def _get_client():
    """Get or create Langfuse client."""
    global _langfuse_client

    if not LANGFUSE_ENABLED:
        return None

    if _langfuse_client is None:
        try:
            from langfuse import Langfuse
            _langfuse_client = Langfuse(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
            )
            logger.info("Langfuse client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}")
            return None

    return _langfuse_client


def create_trace(name: str, session_id: str = None, user_input: str = None, metadata: dict = None):
    """Create a Langfuse trace. Returns trace object or None."""
    if not LANGFUSE_ENABLED:
        return None

    try:
        client = _get_client()
        if client is None:
            return None

        trace = client.trace(
            name=name,
            session_id=session_id,
            input=user_input,
            metadata=metadata or {},
        )
        return trace
    except Exception as e:
        logger.debug(f"Langfuse trace creation skipped: {e}")
        return None


def create_generation(trace, name: str, model: str, messages: list, model_params: dict = None):
    """Create a Langfuse generation span. Returns generation object or None."""
    if not LANGFUSE_ENABLED or trace is None:
        return None

    try:
        generation = trace.generation(
            name=name,
            model=model,
            input=messages,
            model_parameters=model_params or {},
        )
        return generation
    except Exception as e:
        logger.debug(f"Langfuse generation creation skipped: {e}")
        return None


def create_span(trace, name: str, input_data: dict = None):
    """Create a Langfuse span. Returns span object or None."""
    if not LANGFUSE_ENABLED or trace is None:
        return None

    try:
        span = trace.span(
            name=name,
            input=input_data,
        )
        return span
    except Exception as e:
        logger.debug(f"Langfuse span creation skipped: {e}")
        return None


def end_generation(generation, output=None, usage=None):
    """End a Langfuse generation with output and usage."""
    if generation is None:
        return

    try:
        generation.end(output=output, usage=usage)
    except Exception as e:
        logger.debug(f"Langfuse generation end skipped: {e}")


def end_span(span, output=None, level="DEFAULT"):
    """End a Langfuse span with output."""
    if span is None:
        return

    try:
        span.end(output=output, level=level)
    except Exception as e:
        logger.debug(f"Langfuse span end skipped: {e}")


def end_trace(trace, output=None):
    """Update trace with final output."""
    if trace is None:
        return

    try:
        trace.update(output=output)
    except Exception as e:
        logger.debug(f"Langfuse trace update skipped: {e}")


def flush():
    """Flush any pending Langfuse events."""
    if not LANGFUSE_ENABLED:
        return

    try:
        client = _get_client()
        if client:
            client.flush()
    except Exception as e:
        logger.debug(f"Langfuse flush skipped: {e}")
