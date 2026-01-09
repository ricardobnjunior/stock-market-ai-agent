# Stock Market AI Agent

An AI-powered conversational agent that provides real-time stock market information and performs mathematical operations.

## Challenge Requirements Compliance

This project was built to fulfill the EverMe AI Engineer Technical Challenge. Below is a detailed compliance checklist:

### Objective Requirements

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| AI agent with conversational interface | ✅ | Streamlit chat in `src/app.py` |
| Real-time stock market information | ✅ | yfinance integration in `src/tools.py` |
| Mathematical operations | ✅ | `calculate()` function |

### Example Questions from Challenge

| Question | Status | Function |
|----------|--------|----------|
| "What was the Bitcoin price yesterday?" | ✅ | `get_price_yesterday()` |
| "And the current price of Tesla?" | ✅ | `get_current_price()` |
| "What's the percentage change compared to yesterday?" | ✅ | `get_price_change()` |
| "Can you calculate the average stock price of Apple over the last week?" | ✅ | `get_average_price()` |

### Technical Guidelines

| Guideline | Status | Details |
|-----------|--------|---------|
| OpenAI API integration | ✅ | OpenRouter (OpenAI-compatible) in `src/agent.py` |
| Streamlit chat interface | ✅ | `src/app.py` |
| Agentic workflow | ✅ | Tool calling implementation |
| yfinance for market data | ✅ | `src/tools.py` |
| Dockerfile provided | ✅ | `Dockerfile` |

### Deliverables

| Deliverable | Status |
|-------------|--------|
| GitHub repository | ✅ |
| README with instructions | ✅ |
| Support for custom API key | ✅ Via `.env` file |

## Beyond the Requirements

This implementation includes additional features not required by the challenge:

| Extra Feature | Description |
|---------------|-------------|
| **Streaming responses** | Real-time text generation visible to users |
| **Visual feedback** | Status updates showing tool execution in real-time |
| **Price charts** | Interactive line charts for historical data |
| **Stock comparison** | Compare multiple stocks side by side |
| **Cache system** | TTL-based cache to reduce API calls |
| **Rate limiting** | Protection against excessive API usage |
| **Input validation** | Sanitization of user inputs |
| **Logging & metrics** | Error tracking and performance metrics |
| **Unit tests** | Comprehensive test suite with pytest |
| **Multiple data fallbacks** | Robust yfinance integration with 3 fallback methods |
| **Cryptocurrency support** | Bitcoin, Ethereum, and other crypto assets |
| **Conversational context** | Maintains conversation history for follow-up questions |

## Features

- Real-time stock and cryptocurrency prices
- Historical price data with chart visualization
- Price change calculations (daily, weekly)
- Average price calculations
- Stock comparison (up to 5 stocks)
- Mathematical operations
- Streaming conversational interface with visual feedback
- Caching for improved performance
- Rate limiting for API protection

## Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── app.py              # Streamlit chat interface with charts
│   ├── agent.py            # AI agent with OpenRouter integration
│   ├── tools.py            # Stock market tools using yfinance
│   ├── cache.py            # TTL-based caching system
│   ├── rate_limiter.py     # API rate limiting
│   ├── validation.py       # Input validation and sanitization
│   └── logging_config.py   # Logging and metrics
├── tests/
│   ├── __init__.py
│   ├── test_tools.py       # Unit tests for tools
│   └── test_agent.py       # Unit tests for agent
├── .env.example            # Environment variables template
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

## Setup

### 1. Configure Environment Variables

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:

```
OPENROUTER_API_KEY=your_api_key_here
```

### 2. Run with Docker (Recommended)

```bash
# Build the image
docker build -t stock-agent .

# Run the container
docker run -p 8501:8501 stock-agent
```

### 3. Run Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
cd src
streamlit run app.py
```

### 4. Access the Application

Open your browser and navigate to: `http://localhost:8501`

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Using OpenAI API Instead of OpenRouter

To use OpenAI directly, update `src/agent.py` line 23:

```python
OPENROUTER_URL = "https://api.openai.com/v1/chat/completions"
```

And rename `OPENROUTER_API_KEY` to `OPENAI_API_KEY` in your `.env` file.

## Example Questions

- "What's the current price of Tesla?"
- "What was Bitcoin's price yesterday?"
- "What's the percentage change in Apple compared to yesterday?"
- "Calculate the average stock price of NVDA over the last week"
- "Show me a chart of Tesla for the last month"
- "Compare Tesla, Apple and Microsoft"

## Technology Stack

- **LLM**: OpenRouter API (GPT-4o-mini)
- **UI**: Streamlit
- **Market Data**: yfinance
- **Containerization**: Docker
- **Testing**: pytest
