"""Thin convenience wrappers around ``quant_agent.data`` for the Research Agent.

The heavy lifting (yfinance/ccxt fetch, parquet cache read/write, gap-only
re-fetch logic) already lives in ``src/quant_agent/data`` (``MarketDataService``,
``ParquetCache``, ``YFinanceProvider``, ``CCXTProvider``). This module just
exposes a couple of one-call helper functions so a strategy script written by
the Research Agent doesn't need to wire up the service by hand each time.

No new data-fetching or caching logic should be added here — if you need a
new capability, check whether yfinance/ccxt already provides it first.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from quant_agent.data.market_data import MarketDataService

_default_service: Optional[MarketDataService] = None


def _service() -> MarketDataService:
    global _default_service
    if _default_service is None:
        _default_service = MarketDataService()
    return _default_service


def load_equity(
    symbol: str,
    start: datetime,
    end: datetime,
    interval: str = "1d",
) -> pd.DataFrame:
    """Load OHLCV for a stock/ETF ticker via yfinance, cache-first."""
    return _service().get(source="yfinance", symbol=symbol, interval=interval, start=start, end=end)


def load_crypto(
    symbol: str,
    start: datetime,
    end: datetime,
    interval: str = "1h",
    exchange: str = "binance",
) -> pd.DataFrame:
    """Load OHLCV for a crypto pair (e.g. "BTC/USDT") via ccxt, cache-first."""
    return _service().get(
        source="ccxt", symbol=symbol, interval=interval, start=start, end=end, exchange=exchange
    )
