# Stock Market AI Agent

An AI-powered conversational agent that provides real-time stock market information and performs mathematical operations.

## Features

- Real-time stock and cryptocurrency prices
- Historical price data
- Price change calculations (daily, weekly)
- Average price calculations
- Mathematical operations
- Conversational interface

## Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── app.py          # Streamlit chat interface
│   ├── agent.py        # AI agent with OpenRouter integration
│   └── tools.py        # Stock market tools using yfinance
├── .env.example        # Environment variables template
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

## Using OpenAI API Instead of OpenRouter

To use OpenAI directly, update `src/agent.py` line 15:

```python
OPENROUTER_URL = "https://api.openai.com/v1/chat/completions"
```

And rename `OPENROUTER_API_KEY` to `OPENAI_API_KEY` in your `.env` file.

## Example Questions

- "What's the current price of Tesla?"
- "What was Bitcoin's price yesterday?"
- "What's the percentage change in Apple compared to yesterday?"
- "Calculate the average stock price of NVDA over the last week"
- "Compare Tesla and Apple prices"

## Technology Stack

- **LLM**: OpenRouter API (GPT-4o-mini)
- **UI**: Streamlit
- **Market Data**: yfinance
- **Containerization**: Docker
