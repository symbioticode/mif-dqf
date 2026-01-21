# dqf/utils/calendar.py
"""
Calendar utilities for DQF

Provides trading calendar detection and validation.
"""

from typing import List, Literal, Optional

import pandas as pd

CalendarType = Literal["NYSE", "CRYPTO_24_7", "FOREX_24_5", "UNKNOWN"]


def detect_calendar(symbol: str, data: Optional[pd.DataFrame] = None) -> CalendarType:
    """
    Detect appropriate trading calendar based on symbol.

    Uses heuristics based on symbol naming conventions and data patterns.

    Args:
        symbol: Asset symbol (e.g., 'BTC-USD', 'SPY', 'EUR/USD')
        data: Optional DataFrame to analyze patterns

    Returns:
        CalendarType enum

    Examples:
        >>> detect_calendar('BTC-USD')
        'CRYPTO_24_7'
        >>> detect_calendar('SPY')
        'NYSE'
        >>> detect_calendar('EUR/USD')
        'FOREX_24_5'
    """
    symbol_upper = symbol.upper()

    #  IMPORTANT: Check Forex BEFORE Crypto
    # Reason: 'EUR/USD' would match crypto suffix '/USD' if checked first

    # Forex detection (must be before crypto)
    if "/" in symbol:
        base, quote = symbol_upper.split("/")
        # Forex pairs are strictly 3-letter ISO currency codes
        if len(base) == 3 and len(quote) == 3 and base.isalpha() and quote.isalpha():
            return "FOREX_24_5"
        # Otherwise it's likely a crypto pair like DOGE/USD

    # Crypto detection (AFTER Forex check)
    crypto_keywords = ["BTC", "ETH", "SOL", "ADA", "XRP", "DOGE", "USDT", "USDC"]
    crypto_suffixes = ["-USD", "-USDT", "-USDC"]

    for keyword in crypto_keywords:
        if keyword in symbol_upper:
            return "CRYPTO_24_7"

    for suffix in crypto_suffixes:
        if symbol_upper.endswith(suffix):
            return "CRYPTO_24_7"

    # Common stock tickers (NYSE/NASDAQ)
    common_stocks = [
        "SPY",
        "QQQ",
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "NVDA",
        "META",
        "NFLX",
        "TLT",
        "GLD",
        "SLV",
    ]

    if symbol_upper in common_stocks:
        return "NYSE"

    # Length heuristic: Most stock tickers are 1-5 chars
    if len(symbol_upper) <= 5 and symbol_upper.isalpha():
        return "NYSE"

    # If data provided, analyze for weekend pattern
    if data is not None and isinstance(data.index, pd.DatetimeIndex) and len(data) > 30:
        weekend_count = data.index.weekday.isin([5, 6]).sum()
        weekend_ratio = weekend_count / len(data)

        if weekend_ratio > 0.2:  # > 20% weekend data
            return "CRYPTO_24_7"
        elif weekend_ratio < 0.05:  # < 5% weekend data
            return "NYSE"

    return "UNKNOWN"


def is_weekend(date: pd.Timestamp) -> bool:
    """Check if date is Saturday or Sunday."""
    return date.weekday() in [5, 6]


def get_weekends(data: pd.DataFrame) -> pd.DatetimeIndex:
    """
    Get all weekend dates in DataFrame index.

    Args:
        data: DataFrame with DatetimeIndex

    Returns:
        DatetimeIndex of weekend dates
    """
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have DatetimeIndex")

    weekend_mask = data.index.weekday.isin([5, 6])
    return data.index[weekend_mask]


def should_remove_weekends(calendar: CalendarType) -> bool:
    """
    Determine if weekends should be removed for calendar.

    Args:
        calendar: CalendarType

    Returns:
        True if weekends should be removed
    """
    return calendar in ["NYSE", "FOREX_24_5"]


def get_major_us_holidays(year: int) -> List[pd.Timestamp]:
    """
    Get major US market holidays for a given year.

    Note: This is a simplified list. Production should use
    pandas_market_calendars or similar library.

    Args:
        year: Year to get holidays for

    Returns:
        List of Timestamp objects for holidays
    """
    holidays = [
        pd.Timestamp(f"{year}-01-01"),  # New Year's Day
        pd.Timestamp(f"{year}-07-04"),  # Independence Day
        pd.Timestamp(f"{year}-12-25"),  # Christmas
    ]

    # Filter out weekends (markets closed anyway)
    holidays = [h for h in holidays if not is_weekend(h)]

    return holidays
