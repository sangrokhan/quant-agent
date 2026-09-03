from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Optional

Source = Literal["yfinance", "ccxt"]


@dataclass(frozen=True)
class CacheKey:
    source: Source
    symbol: str
    interval: str
    exchange: Optional[str] = None

    def sanitized_symbol(self) -> str:
        return self.symbol.replace("/", "_")

    def cache_path(self, base_dir: str) -> str:
        exchange_part = self.exchange or "_"
        return os.path.join(
            base_dir, self.source, exchange_part, self.sanitized_symbol(), f"{self.interval}.parquet"
        )
