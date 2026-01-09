"""
Stock market tools using yfinance.
Provides functions to fetch real-time and historical market data.
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
import logging

from cache import price_cache, historical_cache, cached
from rate_limiter import yfinance_limiter, rate_limited
from validation import (
    validate_ticker,
    validate_days,
    validate_period,
    validate_expression,
    ValidationError,
)

logger = logging.getLogger(__name__)


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


def _make_price_cache_key(ticker: str) -> str:
    """Generate cache key for price queries."""
    return f"price:{normalize_ticker(ticker)}"


def _make_historical_cache_key(ticker: str, period: str = "1mo") -> str:
    """Generate cache key for historical queries."""
    return f"hist:{normalize_ticker(ticker)}:{period}"


@rate_limited(yfinance_limiter)
@cached(price_cache, key_func=lambda ticker: _make_price_cache_key(ticker))
def get_current_price(ticker: str) -> dict:
    """
    Get current price for a stock or crypto.

    Args:
        ticker: Stock symbol or common name (e.g., 'AAPL', 'Tesla', 'Bitcoin')

    Returns:
        Dictionary with price info or error message
    """
    try:
        ticker = validate_ticker(ticker)
        symbol = normalize_ticker(ticker)
        logger.info(f"Fetching current price for {symbol}")

        stock = yf.Ticker(symbol)

        price = None
        currency = "USD"
        name = symbol

        # Method 1: Try fast_info (most reliable)
        try:
            fast = stock.fast_info
            price = fast.get("lastPrice") or fast.get("regularMarketPrice")
            currency = fast.get("currency", "USD")
        except Exception:
            pass

        # Method 2: Try info dict
        if price is None:
            try:
                info = stock.info
                price = info.get("regularMarketPrice") or info.get("currentPrice")
                currency = info.get("currency", "USD")
                name = info.get("shortName", symbol)
            except Exception:
                pass

        # Method 3: Try history as last resort
        if price is None:
            hist = stock.history(period="5d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])

        if price is None:
            logger.warning(f"Could not fetch price for {symbol}")
            return {"error": f"Could not fetch price for {symbol}. Please try again."}

        logger.info(f"Got price for {symbol}: {price}")
        return {
            "symbol": symbol,
            "price": round(float(price), 2),
            "currency": currency,
            "name": name,
        }
    except ValidationError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return {"error": f"Error fetching {ticker}: {str(e)}"}


@rate_limited(yfinance_limiter)
@cached(price_cache, key_func=lambda ticker: f"yesterday:{normalize_ticker(ticker)}")
def get_price_yesterday(ticker: str) -> dict:
    """
    Get yesterday's closing price for a stock or crypto.

    Args:
        ticker: Stock symbol or common name

    Returns:
        Dictionary with yesterday's price info
    """
    try:
        ticker = validate_ticker(ticker)
        symbol = normalize_ticker(ticker)
        logger.info(f"Fetching yesterday's price for {symbol}")

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
    except ValidationError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error fetching yesterday's price for {ticker}: {e}")
        return {"error": f"Error fetching yesterday's price for {ticker}: {str(e)}"}


@rate_limited(yfinance_limiter)
@cached(price_cache, key_func=lambda ticker: f"change:{normalize_ticker(ticker)}")
def get_price_change(ticker: str) -> dict:
    """
    Calculate percentage change between yesterday and current price.

    Args:
        ticker: Stock symbol or common name

    Returns:
        Dictionary with price change info
    """
    try:
        ticker = validate_ticker(ticker)
        symbol = normalize_ticker(ticker)
        logger.info(f"Calculating price change for {symbol}")

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
    except ValidationError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error calculating price change for {ticker}: {e}")
        return {"error": f"Error calculating price change for {ticker}: {str(e)}"}


@rate_limited(yfinance_limiter)
@cached(historical_cache, key_func=lambda ticker, days=7: f"avg:{normalize_ticker(ticker)}:{days}")
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
        ticker = validate_ticker(ticker)
        days = validate_days(days)
        symbol = normalize_ticker(ticker)
        logger.info(f"Calculating {days}-day average for {symbol}")

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
    except ValidationError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error calculating average for {ticker}: {e}")
        return {"error": f"Error calculating average for {ticker}: {str(e)}"}


@rate_limited(yfinance_limiter)
@cached(historical_cache, key_func=lambda ticker, period="1mo": _make_historical_cache_key(ticker, period))
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
        ticker = validate_ticker(ticker)
        period = validate_period(period)
        symbol = normalize_ticker(ticker)
        logger.info(f"Fetching historical data for {symbol} ({period})")

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
    except ValidationError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker}: {e}")
        return {"error": f"Error fetching historical data for {ticker}: {str(e)}"}


@rate_limited(yfinance_limiter)
def get_chart_data(ticker: str, period: str = "1mo") -> dict:
    """
    Get data formatted for chart visualization.

    Args:
        ticker: Stock symbol or common name
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y)

    Returns:
        Dictionary with chart-ready data
    """
    try:
        ticker = validate_ticker(ticker)
        period = validate_period(period)
        symbol = normalize_ticker(ticker)
        logger.info(f"Fetching chart data for {symbol} ({period})")

        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)

        if hist.empty:
            return {"error": f"No data for {symbol}"}

        # Prepare chart data
        dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        closes = [round(p, 2) for p in hist["Close"].tolist()]
        highs = [round(p, 2) for p in hist["High"].tolist()]
        lows = [round(p, 2) for p in hist["Low"].tolist()]
        volumes = [int(v) for v in hist["Volume"].tolist()]

        return {
            "symbol": symbol,
            "period": period,
            "dates": dates,
            "close": closes,
            "high": highs,
            "low": lows,
            "volume": volumes,
            "data_points": len(dates),
        }
    except ValidationError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error fetching chart data for {ticker}: {e}")
        return {"error": f"Error fetching chart data for {ticker}: {str(e)}"}


@rate_limited(yfinance_limiter)
def compare_stocks(tickers: list[str]) -> dict:
    """
    Compare multiple stocks side by side.

    Args:
        tickers: List of stock symbols or names (max 5)

    Returns:
        Dictionary with comparison data
    """
    try:
        if not tickers:
            return {"error": "No tickers provided"}

        if len(tickers) > 5:
            return {"error": "Maximum 5 tickers allowed for comparison"}

        results = []
        errors = []

        for ticker in tickers:
            try:
                ticker = validate_ticker(ticker)
                symbol = normalize_ticker(ticker)
                stock = yf.Ticker(symbol)
                hist = stock.history(period="5d")

                if len(hist) < 2:
                    errors.append(f"Not enough data for {symbol}")
                    continue

                current = hist["Close"].iloc[-1]
                yesterday = hist["Close"].iloc[-2]
                change = ((current - yesterday) / yesterday) * 100

                # Get additional info
                try:
                    info = stock.info
                    market_cap = info.get("marketCap")
                    name = info.get("shortName", symbol)
                except Exception:
                    market_cap = None
                    name = symbol

                results.append({
                    "symbol": symbol,
                    "name": name,
                    "current_price": round(current, 2),
                    "yesterday_price": round(yesterday, 2),
                    "change_percent": round(change, 2),
                    "market_cap": market_cap,
                })

            except ValidationError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"Error with {ticker}: {str(e)}")

        if not results:
            return {"error": "Could not fetch data for any ticker", "details": errors}

        # Sort by change percentage
        results.sort(key=lambda x: x["change_percent"], reverse=True)

        return {
            "comparison": results,
            "count": len(results),
            "best_performer": results[0]["symbol"],
            "worst_performer": results[-1]["symbol"],
            "errors": errors if errors else None,
        }
    except Exception as e:
        logger.error(f"Error comparing stocks: {e}")
        return {"error": f"Error comparing stocks: {str(e)}"}


def calculate(expression: str) -> dict:
    """
    Safely evaluate a mathematical expression.

    Args:
        expression: Math expression (e.g., '100 * 1.05', '(50 + 30) / 2')

    Returns:
        Dictionary with calculation result
    """
    try:
        expression = validate_expression(expression)
        logger.info(f"Calculating: {expression}")

        result = eval(expression)
        return {
            "expression": expression,
            "result": round(result, 4) if isinstance(result, float) else result,
        }
    except ValidationError as e:
        return {"error": str(e)}
    except ZeroDivisionError:
        return {"error": "Division by zero"}
    except Exception as e:
        logger.error(f"Calculation error: {e}")
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
        "name": "get_chart_data",
        "description": "Get price data formatted for chart visualization. Use when user wants to see a chart or graph.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock symbol or name"
                },
                "period": {
                    "type": "string",
                    "description": "Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y",
                    "default": "1mo"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "compare_stocks",
        "description": "Compare multiple stocks side by side. Shows current prices, changes, and identifies best/worst performers.",
        "parameters": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stock symbols or names to compare (max 5)",
                    "maxItems": 5
                }
            },
            "required": ["tickers"]
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
    "get_chart_data": get_chart_data,
    "compare_stocks": compare_stocks,
    "calculate": calculate,
}
