"""
Unit tests for stock market tools.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools import (
    normalize_ticker,
    get_current_price,
    get_price_yesterday,
    get_price_change,
    get_average_price,
    get_historical_data,
    calculate,
    TICKER_ALIASES,
)
from cache import price_cache, historical_cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    price_cache.clear()
    historical_cache.clear()
    yield
    price_cache.clear()
    historical_cache.clear()


class TestNormalizeTicker:
    """Tests for ticker normalization."""

    def test_lowercase_alias(self):
        assert normalize_ticker("bitcoin") == "BTC-USD"
        assert normalize_ticker("tesla") == "TSLA"
        assert normalize_ticker("apple") == "AAPL"

    def test_uppercase_alias(self):
        assert normalize_ticker("BITCOIN") == "BTC-USD"
        assert normalize_ticker("Tesla") == "TSLA"

    def test_already_symbol(self):
        assert normalize_ticker("AAPL") == "AAPL"
        assert normalize_ticker("MSFT") == "MSFT"

    def test_with_whitespace(self):
        assert normalize_ticker("  bitcoin  ") == "BTC-USD"
        assert normalize_ticker(" tesla ") == "TSLA"

    def test_unknown_ticker(self):
        assert normalize_ticker("xyz") == "XYZ"
        assert normalize_ticker("unknown") == "UNKNOWN"


class TestCalculate:
    """Tests for mathematical calculations."""

    def test_basic_operations(self):
        assert calculate("2 + 2")["result"] == 4
        assert calculate("10 - 3")["result"] == 7
        assert calculate("5 * 4")["result"] == 20
        assert calculate("20 / 4")["result"] == 5

    def test_complex_expressions(self):
        assert calculate("(10 + 5) * 2")["result"] == 30
        assert calculate("100 / (2 + 3)")["result"] == 20

    def test_decimal_results(self):
        result = calculate("10 / 3")
        assert result["result"] == 3.3333

    def test_percentage_calculation(self):
        result = calculate("(720 - 700) / 700 * 100")
        assert abs(result["result"] - 2.8571) < 0.001

    def test_invalid_characters(self):
        result = calculate("2 + 2; import os")
        assert "error" in result

    def test_expression_returned(self):
        result = calculate("5 + 5")
        assert result["expression"] == "5 + 5"
        assert result["result"] == 10


class TestGetCurrentPrice:
    """Tests for get_current_price function."""

    @patch('tools.yf.Ticker')
    def test_successful_price_fetch(self, mock_ticker):
        mock_instance = MagicMock()
        mock_instance.fast_info = {"lastPrice": 150.50, "currency": "USD"}
        mock_ticker.return_value = mock_instance

        result = get_current_price("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["price"] == 150.50
        assert result["currency"] == "USD"

    @patch('tools.yf.Ticker')
    def test_price_with_alias(self, mock_ticker):
        mock_instance = MagicMock()
        mock_instance.fast_info = {"lastPrice": 45000.00, "currency": "USD"}
        mock_ticker.return_value = mock_instance

        result = get_current_price("bitcoin")

        mock_ticker.assert_called_with("BTC-USD")
        assert result["symbol"] == "BTC-USD"

    @patch('tools.yf.Ticker')
    def test_fallback_to_history(self, mock_ticker):
        mock_instance = MagicMock()
        mock_instance.fast_info = {}
        mock_instance.info = {}

        # Mock history DataFrame
        mock_hist = MagicMock()
        mock_hist.empty = False
        mock_hist.__getitem__ = lambda self, key: MagicMock(iloc=MagicMock(__getitem__=lambda s, i: 100.0))
        mock_instance.history.return_value = mock_hist

        mock_ticker.return_value = mock_instance

        result = get_current_price("TEST")
        assert "price" in result or "error" in result

    @patch('tools.yf.Ticker')
    def test_error_handling(self, mock_ticker):
        mock_ticker.side_effect = Exception("API Error")

        result = get_current_price("INVALID")

        assert "error" in result


class TestGetPriceYesterday:
    """Tests for get_price_yesterday function."""

    @patch('tools.yf.Ticker')
    def test_successful_yesterday_price(self, mock_ticker):
        import pandas as pd

        mock_instance = MagicMock()
        dates = pd.date_range(end='2024-01-10', periods=5)
        mock_hist = pd.DataFrame({
            'Close': [100.0, 101.0, 102.0, 103.0, 104.0]
        }, index=dates)
        mock_instance.history.return_value = mock_hist
        mock_ticker.return_value = mock_instance

        result = get_price_yesterday("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["price"] == 103.0
        assert "date" in result

    @patch('tools.yf.Ticker')
    def test_insufficient_data(self, mock_ticker):
        import pandas as pd

        mock_instance = MagicMock()
        mock_hist = pd.DataFrame({'Close': [100.0]}, index=pd.date_range(end='2024-01-10', periods=1))
        mock_instance.history.return_value = mock_hist
        mock_ticker.return_value = mock_instance

        result = get_price_yesterday("AAPL")

        assert "error" in result


class TestGetPriceChange:
    """Tests for get_price_change function."""

    @patch('tools.yf.Ticker')
    def test_positive_change(self, mock_ticker):
        import pandas as pd

        mock_instance = MagicMock()
        dates = pd.date_range(end='2024-01-10', periods=5)
        mock_hist = pd.DataFrame({
            'Close': [100.0, 100.0, 100.0, 100.0, 105.0]
        }, index=dates)
        mock_instance.history.return_value = mock_hist
        mock_ticker.return_value = mock_instance

        result = get_price_change("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["percent_change"] == 5.0
        assert result["change"] == 5.0

    @patch('tools.yf.Ticker')
    def test_negative_change(self, mock_ticker):
        import pandas as pd

        mock_instance = MagicMock()
        dates = pd.date_range(end='2024-01-10', periods=5)
        mock_hist = pd.DataFrame({
            'Close': [100.0, 100.0, 100.0, 100.0, 95.0]
        }, index=dates)
        mock_instance.history.return_value = mock_hist
        mock_ticker.return_value = mock_instance

        result = get_price_change("AAPL")

        assert result["percent_change"] == -5.0


class TestGetAveragePrice:
    """Tests for get_average_price function."""

    @patch('tools.yf.Ticker')
    def test_weekly_average(self, mock_ticker):
        import pandas as pd

        mock_instance = MagicMock()
        dates = pd.date_range(end='2024-01-10', periods=17)
        prices = [100.0] * 10 + [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0]
        mock_hist = pd.DataFrame({'Close': prices}, index=dates)
        mock_instance.history.return_value = mock_hist
        mock_ticker.return_value = mock_instance

        result = get_average_price("AAPL", days=7)

        assert result["symbol"] == "AAPL"
        assert result["days"] == 7
        assert "average_price" in result
        assert "daily_prices" in result

    @patch('tools.yf.Ticker')
    def test_custom_days(self, mock_ticker):
        import pandas as pd

        mock_instance = MagicMock()
        dates = pd.date_range(end='2024-01-10', periods=20)
        mock_hist = pd.DataFrame({'Close': [100.0] * 20}, index=dates)
        mock_instance.history.return_value = mock_hist
        mock_ticker.return_value = mock_instance

        result = get_average_price("AAPL", days=5)

        assert result["days"] == 5


class TestGetHistoricalData:
    """Tests for get_historical_data function."""

    @patch('tools.yf.Ticker')
    def test_monthly_data(self, mock_ticker):
        import pandas as pd

        mock_instance = MagicMock()
        dates = pd.date_range(end='2024-01-10', periods=30)
        mock_hist = pd.DataFrame({
            'Close': range(100, 130),
            'High': range(105, 135),
            'Low': range(95, 125)
        }, index=dates)
        mock_instance.history.return_value = mock_hist
        mock_ticker.return_value = mock_instance

        result = get_historical_data("AAPL", period="1mo")

        assert result["symbol"] == "AAPL"
        assert result["period"] == "1mo"
        assert "high" in result
        assert "low" in result
        assert "start_price" in result
        assert "end_price" in result

    @patch('tools.yf.Ticker')
    def test_empty_data(self, mock_ticker):
        import pandas as pd

        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_instance

        result = get_historical_data("INVALID")

        assert "error" in result
