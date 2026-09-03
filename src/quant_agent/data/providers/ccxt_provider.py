from __future__ import annotations

from datetime import datetime

import ccxt
import pandas as pd

from .base import MarketDataFetchError, MarketDataProvider

_NS_PER_MS = 10**6
_OUTPUT_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


class CCXTProvider(MarketDataProvider):
    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id
        try:
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({"enableRateLimit": True})
        except Exception as exc:
            raise MarketDataFetchError(
                f"unknown or unsupported ccxt exchange: {exchange_id}"
            ) from exc

    def fetch(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        since = pd.Timestamp(start, tz="UTC").value // _NS_PER_MS
        end_ms = pd.Timestamp(end, tz="UTC").value // _NS_PER_MS
        rows: list[list] = []
        try:
            while since < end_ms:
                batch = self.exchange.fetch_ohlcv(symbol, timeframe=interval, since=since, limit=1000)
                if not batch:
                    break
                rows.extend(batch)
                last_ts = batch[-1][0]
                if last_ts <= since:
                    break
                since = last_ts + 1

            if not rows:
                return pd.DataFrame(columns=_OUTPUT_COLUMNS)

            df = pd.DataFrame(rows, columns=_OUTPUT_COLUMNS)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            start_ts = pd.Timestamp(start, tz="UTC")
            end_ts = pd.Timestamp(end, tz="UTC")
            df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)]
            return df.reset_index(drop=True)
        except Exception as exc:
            raise MarketDataFetchError(
                f"ccxt fetch failed for {symbol} on {self.exchange_id}: {exc}"
            ) from exc
