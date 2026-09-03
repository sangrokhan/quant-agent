from __future__ import annotations

from datetime import datetime

import pandas as pd
import yfinance as yf

from .base import MarketDataFetchError, MarketDataProvider

_COLUMN_MAP = {
    "Date": "timestamp",
    "Datetime": "timestamp",
    "index": "timestamp",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}

_OUTPUT_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


class YFinanceProvider(MarketDataProvider):
    def fetch(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        try:
            raw = yf.download(
                symbol,
                start=start,
                end=end,
                interval=interval,
                progress=False,
                auto_adjust=False,
            )
        except Exception as exc:
            raise MarketDataFetchError(f"yfinance fetch failed for {symbol}: {exc}") from exc

        if raw is None or raw.empty:
            return pd.DataFrame(columns=_OUTPUT_COLUMNS)

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        df = raw.reset_index().rename(columns=_COLUMN_MAP)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df[_OUTPUT_COLUMNS]
