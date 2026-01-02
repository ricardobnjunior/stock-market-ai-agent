"""
Stock market tools using yfinance.
Provides functions to fetch real-time and historical market data.
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional


# Common ticker mappings for crypto and popular assets
TICKER_ALIASES = {
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "ethereum": "ETH-USD",
    "eth": "ETH-USD",
    "tesla": "TSLA",
    "apple": "AAPL",
    "google": "GOOGL",
    "amazon": "AMZN",
    "microsoft": "MSFT",
    "meta": "META",
    "facebook": "META",
    "nvidia": "NVDA",
    "netflix": "NFLX",
}


def normalize_ticker(ticker: str) -> str:
    """Convert common names to ticker symbols."""
    normalized = ticker.lower().strip()
    return TICKER_ALIASES.get(normalized, ticker.upper())


def get_current_price(ticker: str) -> dict:
    """
    Get current price for a stock or crypto.

    Args:
        ticker: Stock symbol or common name (e.g., 'AAPL', 'Tesla', 'Bitcoin')

    Returns:
        Dictionary with price info or error message
    """
    try:
        symbol = normalize_ticker(ticker)
        stock = yf.Ticker(symbol)

        price = None
        currency = "USD"
        name = symbol

        # Method 1: Try fast_info (most reliable)
        try:
            fast = stock.fast_info
            price = fast.get("lastPrice") or fast.get("regularMarketPrice")
            currency = fast.get("currency", "USD")
        except:
            pass

        # Method 2: Try info dict
        if price is None:
            try:
                info = stock.info
                price = info.get("regularMarketPrice") or info.get("currentPrice")
                currency = info.get("currency", "USD")
                name = info.get("shortName", symbol)
            except:
                pass

        # Method 3: Try history as last resort
        if price is None:
            hist = stock.history(period="5d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])

        if price is None:
            return {"error": f"Could not fetch price for {symbol}. Please try again."}

        return {
            "symbol": symbol,
            "price": round(float(price), 2),
            "currency": currency,
            "name": name,
        }
    except Exception as e:
        return {"error": f"Error fetching {ticker}: {str(e)}"}


def get_price_yesterday(ticker: str) -> dict:
    """
    Get yesterday's closing price for a stock or crypto.

    Args:
        ticker: Stock symbol or common name

    Returns:
        Dictionary with yesterday's price info
    """
    try:
        symbol = normalize_ticker(ticker)
        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d")

        if len(hist) < 2:
            return {"error": f"Not enough historical data for {symbol}"}

        yesterday_close = hist["Close"].iloc[-2]
        yesterday_date = hist.index[-2].strftime("%Y-%m-%d")

        return {
            "symbol": symbol,
            "price": round(yesterday_close, 2),
            "date": yesterday_date,
        }
    except Exception as e:
        return {"error": f"Error fetching yesterday's price for {ticker}: {str(e)}"}


def get_price_change(ticker: str) -> dict:
    """
    Calculate percentage change between yesterday and current price.

    Args:
        ticker: Stock symbol or common name

    Returns:
        Dictionary with price change info
    """
    try:
        symbol = normalize_ticker(ticker)
        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d")

        if len(hist) < 2:
            return {"error": f"Not enough data for {symbol}"}

        current_price = hist["Close"].iloc[-1]
        yesterday_price = hist["Close"].iloc[-2]

        change = current_price - yesterday_price
        percent_change = (change / yesterday_price) * 100

        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "yesterday_price": round(yesterday_price, 2),
            "change": round(change, 2),
            "percent_change": round(percent_change, 2),
        }
    except Exception as e:
        return {"error": f"Error calculating price change for {ticker}: {str(e)}"}


def get_average_price(ticker: str, days: int = 7) -> dict:
    """
    Calculate average closing price over a period.

    Args:
        ticker: Stock symbol or common name
        days: Number of days to average (default: 7)

    Returns:
        Dictionary with average price info
    """
    try:
        symbol = normalize_ticker(ticker)
        stock = yf.Ticker(symbol)
        hist = stock.history(period=f"{days + 10}d")

        if len(hist) < days:
            return {"error": f"Not enough data for {days}-day average of {symbol}"}

        recent = hist.tail(days)
        avg_price = recent["Close"].mean()

        prices = [round(p, 2) for p in recent["Close"].tolist()]
        dates = [d.strftime("%Y-%m-%d") for d in recent.index]

        return {
            "symbol": symbol,
            "average_price": round(avg_price, 2),
            "days": len(recent),
            "period_start": dates[0],
            "period_end": dates[-1],
            "daily_prices": dict(zip(dates, prices)),
        }
    except Exception as e:
        return {"error": f"Error calculating average for {ticker}: {str(e)}"}


def get_historical_data(ticker: str, period: str = "1mo") -> dict:
    """
    Get historical price data.

    Args:
        ticker: Stock symbol or common name
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)

    Returns:
        Dictionary with historical data
    """
    try:
        symbol = normalize_ticker(ticker)
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)

        if hist.empty:
            return {"error": f"No historical data for {symbol}"}

        return {
            "symbol": symbol,
            "period": period,
            "data_points": len(hist),
            "high": round(hist["High"].max(), 2),
            "low": round(hist["Low"].min(), 2),
            "start_price": round(hist["Close"].iloc[0], 2),
            "end_price": round(hist["Close"].iloc[-1], 2),
            "start_date": hist.index[0].strftime("%Y-%m-%d"),
            "end_date": hist.index[-1].strftime("%Y-%m-%d"),
        }
    except Exception as e:
        return {"error": f"Error fetching historical data for {ticker}: {str(e)}"}


def calculate(expression: str) -> dict:
    """
    Safely evaluate a mathematical expression.

    Args:
        expression: Math expression (e.g., '100 * 1.05', '(50 + 30) / 2')

    Returns:
        Dictionary with calculation result
    """
    try:
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return {"error": "Invalid characters in expression"}

        result = eval(expression)
        return {
            "expression": expression,
            "result": round(result, 4) if isinstance(result, float) else result,
        }
    except Exception as e:
        return {"error": f"Calculation error: {str(e)}"}


# Tool definitions for the agent
TOOLS = [
    {
        "name": "get_current_price",
        "description": "Get the current price of a stock or cryptocurrency. Use this for questions about current/latest prices.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock symbol or name (e.g., 'AAPL', 'Tesla', 'Bitcoin', 'BTC')"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_price_yesterday",
        "description": "Get yesterday's closing price for a stock or cryptocurrency.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock symbol or name"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_price_change",
        "description": "Get the price change and percentage change compared to yesterday.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock symbol or name"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_average_price",
        "description": "Calculate the average closing price over a specified number of days.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock symbol or name"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to calculate average (default: 7)",
                    "default": 7
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_historical_data",
        "description": "Get historical price data including high, low, and price range for a period.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock symbol or name"
                },
                "period": {
                    "type": "string",
                    "description": "Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max",
                    "default": "1mo"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "calculate",
        "description": "Perform mathematical calculations. Use for percentage calculations, averages, or any math operations.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '100 * 1.05', '(720 - 700) / 700 * 100')"
                }
            },
            "required": ["expression"]
        }
    }
]


# Function registry for easy lookup
TOOL_FUNCTIONS = {
    "get_current_price": get_current_price,
    "get_price_yesterday": get_price_yesterday,
    "get_price_change": get_price_change,
    "get_average_price": get_average_price,
    "get_historical_data": get_historical_data,
    "calculate": calculate,
}
