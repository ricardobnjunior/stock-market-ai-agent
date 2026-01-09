"""
Input validation and sanitization.
"""

import re
from typing import Optional


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_ticker(ticker: str) -> str:
    """
    Validate and sanitize ticker symbol.

    Args:
        ticker: Raw ticker input

    Returns:
        Sanitized ticker string

    Raises:
        ValidationError: If ticker is invalid
    """
    if not ticker:
        raise ValidationError("Ticker symbol cannot be empty")

    # Strip whitespace
    ticker = ticker.strip()

    if len(ticker) > 20:
        raise ValidationError("Ticker symbol too long (max 20 characters)")

    # Allow alphanumeric, dash, dot (for crypto pairs like BTC-USD)
    if not re.match(r'^[A-Za-z0-9\-\.]+$', ticker):
        raise ValidationError(
            "Ticker contains invalid characters. "
            "Only letters, numbers, dash, and dot are allowed."
        )

    return ticker


def validate_days(days: int) -> int:
    """
    Validate days parameter for historical queries.

    Args:
        days: Number of days

    Returns:
        Validated days value

    Raises:
        ValidationError: If days is invalid
    """
    if not isinstance(days, int):
        try:
            days = int(days)
        except (ValueError, TypeError):
            raise ValidationError("Days must be a number")

    if days < 1:
        raise ValidationError("Days must be at least 1")

    if days > 365:
        raise ValidationError("Days cannot exceed 365")

    return days


def validate_period(period: str) -> str:
    """
    Validate period parameter for historical data.

    Args:
        period: Time period string

    Returns:
        Validated period

    Raises:
        ValidationError: If period is invalid
    """
    valid_periods = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}

    period = period.lower().strip()

    if period not in valid_periods:
        raise ValidationError(
            f"Invalid period '{period}'. "
            f"Valid options: {', '.join(sorted(valid_periods))}"
        )

    return period


def validate_expression(expression: str) -> str:
    """
    Validate and sanitize mathematical expression.

    Args:
        expression: Math expression to validate

    Returns:
        Sanitized expression

    Raises:
        ValidationError: If expression is invalid or potentially dangerous
    """
    if not expression:
        raise ValidationError("Expression cannot be empty")

    expression = expression.strip()

    if len(expression) > 200:
        raise ValidationError("Expression too long (max 200 characters)")

    # Strict whitelist of allowed characters
    allowed = set("0123456789+-*/.() ")

    invalid_chars = set(expression) - allowed
    if invalid_chars:
        raise ValidationError(
            f"Expression contains invalid characters: {', '.join(repr(c) for c in invalid_chars)}"
        )

    # Check for balanced parentheses
    depth = 0
    for char in expression:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        if depth < 0:
            raise ValidationError("Unbalanced parentheses in expression")

    if depth != 0:
        raise ValidationError("Unbalanced parentheses in expression")

    # Prevent division by zero patterns
    if re.search(r'/\s*0(?![0-9.])', expression):
        raise ValidationError("Division by zero detected")

    return expression


def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """
    General sanitization for user text input.

    Args:
        text: User input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Strip and limit length
    text = text.strip()[:max_length]

    # Remove null bytes and other control characters (keep newlines/tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text
