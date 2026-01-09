"""
Unit tests for the AI agent.
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent import (
    get_api_key,
    execute_tool,
    parse_sse_stream,
    SYSTEM_PROMPT,
    TOOL_DESCRIPTIONS,
)


class TestGetApiKey:
    """Tests for API key retrieval."""

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-123"})
    def test_valid_api_key(self):
        key = get_api_key()
        assert key == "test-key-123"

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key(self):
        # Remove the key if it exists
        os.environ.pop("OPENROUTER_API_KEY", None)
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY not found"):
            get_api_key()


class TestExecuteTool:
    """Tests for tool execution."""

    @patch('agent.TOOL_FUNCTIONS')
    def test_execute_known_tool(self, mock_functions):
        mock_functions.__contains__ = lambda self, x: x == "get_current_price"
        mock_functions.__getitem__ = lambda self, x: lambda ticker: {"price": 150.0, "symbol": ticker}

        result = execute_tool("get_current_price", {"ticker": "AAPL"})
        parsed = json.loads(result)

        assert parsed["price"] == 150.0
        assert parsed["symbol"] == "AAPL"

    def test_execute_unknown_tool(self):
        result = execute_tool("unknown_tool", {})
        parsed = json.loads(result)

        assert "error" in parsed
        assert "Unknown tool" in parsed["error"]

    @patch('agent.TOOL_FUNCTIONS')
    def test_execute_calculate(self, mock_functions):
        mock_functions.__contains__ = lambda self, x: x == "calculate"
        mock_functions.__getitem__ = lambda self, x: lambda expression: {"result": 4, "expression": expression}

        result = execute_tool("calculate", {"expression": "2 + 2"})
        parsed = json.loads(result)

        assert parsed["result"] == 4


class TestParseSSEStream:
    """Tests for SSE stream parsing."""

    def test_parse_content_chunks(self):
        # Simulate SSE response
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            b'data: {"choices": [{"delta": {"content": " World"}}]}',
            b'data: [DONE]',
        ]

        chunks = list(parse_sse_stream(mock_response))

        assert chunks == ["Hello", " World"]

    def test_parse_empty_content(self):
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'data: {"choices": [{"delta": {}}]}',
            b'data: [DONE]',
        ]

        chunks = list(parse_sse_stream(mock_response))

        assert chunks == []

    def test_parse_invalid_json(self):
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'data: invalid json',
            b'data: {"choices": [{"delta": {"content": "Valid"}}]}',
            b'data: [DONE]',
        ]

        chunks = list(parse_sse_stream(mock_response))

        assert chunks == ["Valid"]


class TestSystemPrompt:
    """Tests for system prompt configuration."""

    def test_prompt_contains_capabilities(self):
        assert "stock" in SYSTEM_PROMPT.lower()
        assert "crypto" in SYSTEM_PROMPT.lower()
        assert "calculation" in SYSTEM_PROMPT.lower()

    def test_prompt_contains_ticker_mappings(self):
        assert "Bitcoin" in SYSTEM_PROMPT
        assert "BTC-USD" in SYSTEM_PROMPT
        assert "Tesla" in SYSTEM_PROMPT
        assert "TSLA" in SYSTEM_PROMPT


class TestToolDescriptions:
    """Tests for tool descriptions."""

    def test_all_tools_have_descriptions(self):
        expected_tools = [
            "get_current_price",
            "get_price_yesterday",
            "get_price_change",
            "get_average_price",
            "get_historical_data",
            "calculate",
        ]

        for tool in expected_tools:
            assert tool in TOOL_DESCRIPTIONS
            assert len(TOOL_DESCRIPTIONS[tool]) > 0
