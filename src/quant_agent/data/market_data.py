from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from .cache import ParquetCache
from .models import CacheKey, Source
from .providers.base import MarketDataProvider
from .providers.ccxt_provider import CCXTProvider
from .providers.yfinance_provider import YFinanceProvider


class MarketDataService:
    def __init__(self, cache: Optional[ParquetCache] = None):
        self.cache = cache or ParquetCache()
        self._providers: Dict[str, MarketDataProvider] = {
            "yfinance": YFinanceProvider(),
        }
        self._ccxt_providers: Dict[str, MarketDataProvider] = {}

    def _provider_for(self, source: Source, exchange: Optional[str]) -> MarketDataProvider:
        if source == "yfinance":
            return self._providers["yfinance"]
        if source == "ccxt":
            exchange_id = exchange or "binance"
            if exchange_id not in self._ccxt_providers:
                self._ccxt_providers[exchange_id] = CCXTProvider(exchange_id=exchange_id)
            return self._ccxt_providers[exchange_id]
        raise ValueError(f"unknown source: {source}")

    def get(
        self,
        source: Source,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        exchange: Optional[str] = None,
    ) -> pd.DataFrame:
        key = CacheKey(source=source, symbol=symbol, interval=interval, exchange=exchange)
        coverage = self.cache.get_coverage(key)
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")

        if coverage is not None and coverage[0] <= start_ts and coverage[1] >= end_ts:
            self.cache.log_hit(key, start, end)
            return self.cache.read(key, start, end)

        self.cache.log_miss(key, start, end)
        provider = self._provider_for(source, exchange)

        if coverage is None:
            fetched = provider.fetch(symbol, interval, start, end)
            if fetched.empty:
                return fetched
            self.cache.write(key, fetched)
            return self.cache.read(key, start, end)

        cov_start, cov_end = coverage
        if start_ts < cov_start:
            gap = provider.fetch(symbol, interval, start, cov_start.to_pydatetime())
            if not gap.empty:
                self.cache.write(key, gap)
        if end_ts > cov_end:
            gap = provider.fetch(symbol, interval, cov_end.to_pydatetime(), end)
            if not gap.empty:
                self.cache.write(key, gap)
        return self.cache.read(key, start, end)
