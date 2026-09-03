from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class MarketDataFetchError(Exception):
    """Raised when a provider fails to fetch market data."""


class MarketDataProvider(ABC):
    @abstractmethod
    def fetch(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Return an OHLCV DataFrame (timestamp, open, high, low, close, volume) covering [start, end]."""
        raise NotImplementedError
