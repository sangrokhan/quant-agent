from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd

from .models import CacheKey

logger = logging.getLogger("quant_agent.data.cache")

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def to_utc_timestamp(dt: datetime) -> pd.Timestamp:
    """Coerce a naive or tz-aware datetime/Timestamp to a UTC pd.Timestamp.

    ``pd.Timestamp(dt, tz="UTC")`` raises when ``dt`` already carries
    tzinfo -- callers throughout this data layer (and strategy code that
    re-derives start/end from an already-UTC-aware price_df.index) may pass
    either naive or tz-aware datetimes, so always go through this helper
    instead of the bare constructor.
    """
    ts = pd.Timestamp(dt)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


class ParquetCache:
    def __init__(self, base_dir: str = "data/cache"):
        self.base_dir = base_dir

    def get_coverage(self, key: CacheKey) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
        path = key.cache_path(self.base_dir)
        if not os.path.exists(path):
            return None
        df = pd.read_parquet(path, columns=["timestamp"])
        if df.empty:
            return None
        return df["timestamp"].min(), df["timestamp"].max()

    def covers(self, key: CacheKey, start: datetime, end: datetime) -> bool:
        coverage = self.get_coverage(key)
        if coverage is None:
            return False
        cov_start, cov_end = coverage
        return cov_start <= to_utc_timestamp(start) and cov_end >= to_utc_timestamp(end)

    def read(self, key: CacheKey, start: datetime, end: datetime) -> pd.DataFrame:
        path = key.cache_path(self.base_dir)
        df = pd.read_parquet(path)
        start_ts = to_utc_timestamp(start)
        end_ts = to_utc_timestamp(end)
        mask = (df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)
        return df.loc[mask].sort_values("timestamp").reset_index(drop=True)

    def write(self, key: CacheKey, df: pd.DataFrame) -> None:
        path = key.cache_path(self.base_dir)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            existing = pd.read_parquet(path)
            combined = pd.concat([existing, df], ignore_index=True)
        else:
            combined = df
        combined = (
            combined.drop_duplicates(subset="timestamp", keep="last")
            .sort_values("timestamp")
            .reset_index(drop=True)
        )
        combined.to_parquet(path, index=False)

    def log_hit(self, key: CacheKey, start: datetime, end: datetime) -> None:
        logger.info(
            "cache_hit source=%s exchange=%s symbol=%s interval=%s start=%s end=%s",
            key.source, key.exchange, key.symbol, key.interval, start, end,
        )

    def log_miss(self, key: CacheKey, start: datetime, end: datetime) -> None:
        logger.info(
            "cache_miss source=%s exchange=%s symbol=%s interval=%s start=%s end=%s",
            key.source, key.exchange, key.symbol, key.interval, start, end,
        )
