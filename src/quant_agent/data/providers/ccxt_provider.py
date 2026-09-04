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

    @staticmethod
    def _to_utc_timestamp(dt: datetime) -> pd.Timestamp:
        """Coerce a naive or tz-aware datetime to a UTC pd.Timestamp.

        ``pd.Timestamp(dt, tz="UTC")`` raises when ``dt`` already carries
        tzinfo (e.g. gap-fetch callers in market_data.py pass back an
        already-UTC-aware datetime from ``cov_start.to_pydatetime()``) --
        use tz_localize/tz_convert instead so both naive and tz-aware
        datetimes work.
        """
        ts = pd.Timestamp(dt)
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

    def fetch(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        since = self._to_utc_timestamp(start).value // _NS_PER_MS
        end_ms = self._to_utc_timestamp(end).value // _NS_PER_MS
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
            start_ts = self._to_utc_timestamp(start)
            end_ts = self._to_utc_timestamp(end)
            df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)]
            return df.reset_index(drop=True)
        except Exception as exc:
            raise MarketDataFetchError(
                f"ccxt fetch failed for {symbol} on {self.exchange_id}: {exc}"
            ) from exc
