# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (from project root)
cd src && streamlit run app.py

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Run with Docker
docker build -t stock-agent .
docker run -p 8501:8501 stock-agent

# Access the app
open http://localhost:8501
```

## Architecture

This is a Stock Market AI Agent with a tool-calling architecture:

```
app.py (Streamlit UI) → agent.py (LLM orchestration) → tools.py (yfinance data)
                                    ↓
                        cache.py, rate_limiter.py, validation.py, logging_config.py
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `app.py` | Streamlit chat UI with streaming, charts, and comparison tables |
| `agent.py` | LLM orchestration via OpenRouter, tool execution loop |
| `tools.py` | 8 tool functions using yfinance for market data |

### Support Modules

| Module | Purpose |
|--------|---------|
| `cache.py` | TTL-based cache (30s for prices, 5min for historical) |
| `rate_limiter.py` | Token bucket rate limiter for API protection |
| `validation.py` | Input sanitization for tickers, expressions, periods |
| `logging_config.py` | Logging setup and metrics collection |

### Flow
1. **app.py**: Chat interface with streaming. Calls `run_agent_with_streaming()` and yields status updates, tool results, charts, and text chunks.

2. **agent.py**: First LLM call (non-streaming) determines if tools are needed. Executes tools with metrics tracking. Second streaming call for final response.

3. **tools.py**: Eight tool functions with decorators for caching, rate limiting, and validation. Returns dict with data or `{"error": "..."}`.

### Key Patterns
- Tool definitions follow OpenAI function-calling format
- `normalize_ticker()` maps common names (e.g., "bitcoin" → "BTC-USD")
- Decorators stack: `@rate_limited` → `@cached` → function
- Agent yields generator with mixed types: `dict` for status/tool results, `str` for text

### Available Tools
- `get_current_price` - Current stock/crypto price
- `get_price_yesterday` - Previous day closing price
- `get_price_change` - Price change with percentage
- `get_average_price` - Average over N days
- `get_historical_data` - Historical high/low/range
- `get_chart_data` - Data formatted for Streamlit charts
- `compare_stocks` - Compare up to 5 stocks side by side
- `calculate` - Safe math expression evaluation

## Configuration

- **API Key**: Set `OPENROUTER_API_KEY` in `.env`
- **Model**: `openai/gpt-4o-mini` (configurable in `agent.py:24`)
- **Cache TTL**: 30s prices, 300s historical (in `cache.py`)
- **Rate Limits**: 30 req/min yfinance, 20 req/min LLM (in `rate_limiter.py`)
- **To use OpenAI directly**: Change `OPENROUTER_URL` to `https://api.openai.com/v1/chat/completions`
