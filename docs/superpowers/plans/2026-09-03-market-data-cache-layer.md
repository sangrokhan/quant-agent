# Market Data Cache Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the `quant-agent` repo and build a local-first market data layer (yfinance + ccxt) with a coverage-aware Parquet cache so no symbol/interval/range is ever fetched twice.

**Architecture:** A `MarketDataService` is the single entry point. It checks a `ParquetCache` (one Parquet file per source/exchange/symbol/interval) for coverage of the requested date range; on any gap it calls the matching `MarketDataProvider` (`YFinanceProvider` or `CCXTProvider`) for only the missing sub-range(s), merges the result into the cache, then serves the read from the cache.

**Tech Stack:** Python 3.11+, `uv`, `pandas`, `pyarrow` (Parquet), `yfinance`, `ccxt`, `pytest`.

**Spec:** `docs/superpowers/specs/2026-09-03-market-data-cache-layer-design.md`

## Global Constraints

- Fixed OHLCV schema everywhere: `timestamp (UTC, tz-aware), open, high, low, close, volume`.
- No provider `fetch()` call is made for a symbol/interval/range already fully covered by the local cache.
- `fetch()` failures raise `MarketDataFetchError` — no retry logic in this layer.
- Real network calls only happen in tests marked `@pytest.mark.integration`, excluded from the default `pytest` run via `pyproject.toml`.
- `data/cache/` is never committed to git.

---

### Task 1: Repo scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/quant_agent/__init__.py`
- Create: `src/quant_agent/data/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/data/__init__.py`
- Test: `tests/test_package.py`

**Interfaces:**
- Produces: importable package `quant_agent` that later tasks add modules under `quant_agent.data`.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "quant-agent"
version = "0.1.0"
description = "Autonomous quant research Ralph loop system"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.2",
    "pyarrow>=17.0",
    "yfinance>=0.2.40",
    "ccxt>=4.3",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
]

[tool.pytest.ini_options]
markers = [
    "integration: hits real network APIs, excluded by default",
]
addopts = "-m 'not integration'"
testpaths = ["tests"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/quant_agent"]
```

- [ ] **Step 2: Create `.gitignore`**

```
data/cache/
__pycache__/
*.pyc
.venv/
.env
*.egg-info/
.pytest_cache/
```

- [ ] **Step 3: Create `.env.example`**

```
# Reserved for future ccxt exchange API keys / config.
# No keys are required for the public market data endpoints used in this sub-project.
```

- [ ] **Step 4: Create empty package/test `__init__.py` files and package docstring**

`src/quant_agent/__init__.py`:
```python
"""quant_agent: autonomous quant research system."""
```

`src/quant_agent/data/__init__.py`:
```python
```

`tests/__init__.py`:
```python
```

`tests/data/__init__.py`:
```python
```

- [ ] **Step 5: Write the smoke test**

`tests/test_package.py`:
```python
import quant_agent


def test_package_importable():
    assert quant_agent is not None
```

- [ ] **Step 6: Sync deps and run the test**

Run: `uv sync && uv run pytest tests/test_package.py -v`
Expected: PASS (1 test)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore .env.example src tests uv.lock
git commit -m "chore: scaffold quant-agent repo with uv"
```

---

### Task 2: `CacheKey` model

**Files:**
- Create: `src/quant_agent/data/models.py`
- Test: `tests/data/test_models.py`

**Interfaces:**
- Produces: `CacheKey(source: Literal["yfinance", "ccxt"], symbol: str, interval: str, exchange: str | None = None)` with methods `sanitized_symbol() -> str` and `cache_path(base_dir: str) -> str`. Later tasks (`ParquetCache`, `MarketDataService`) import `CacheKey` and the `Source` type alias from this module.

- [ ] **Step 1: Write the failing test**

`tests/data/test_models.py`:
```python
from quant_agent.data.models import CacheKey


def test_sanitized_symbol_replaces_slash():
    key = CacheKey(source="ccxt", symbol="BTC/USDT", interval="1h", exchange="binance")
    assert key.sanitized_symbol() == "BTC_USDT"


def test_sanitized_symbol_no_slash_unchanged():
    key = CacheKey(source="yfinance", symbol="AAPL", interval="1d")
    assert key.sanitized_symbol() == "AAPL"


def test_cache_path_yfinance_uses_underscore_for_missing_exchange():
    key = CacheKey(source="yfinance", symbol="AAPL", interval="1d")
    path = key.cache_path("data/cache")
    assert path == "data/cache/yfinance/_/AAPL/1d.parquet"


def test_cache_path_ccxt_includes_exchange():
    key = CacheKey(source="ccxt", symbol="BTC/USDT", interval="1h", exchange="binance")
    path = key.cache_path("data/cache")
    assert path == "data/cache/ccxt/binance/BTC_USDT/1h.parquet"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quant_agent.data.models'`

- [ ] **Step 3: Write the implementation**

`src/quant_agent/data/models.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_models.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/quant_agent/data/models.py tests/data/test_models.py
git commit -m "feat: add CacheKey model"
```

---

### Task 3: `ParquetCache`

**Files:**
- Create: `src/quant_agent/data/cache.py`
- Test: `tests/data/test_cache.py`

**Interfaces:**
- Consumes: `CacheKey` from `quant_agent.data.models` (Task 2).
- Produces: `ParquetCache(base_dir: str = "data/cache")` with:
  - `get_coverage(key: CacheKey) -> tuple[pd.Timestamp, pd.Timestamp] | None`
  - `covers(key: CacheKey, start: datetime, end: datetime) -> bool`
  - `read(key: CacheKey, start: datetime, end: datetime) -> pd.DataFrame`
  - `write(key: CacheKey, df: pd.DataFrame) -> None`
  - `log_hit(key, start, end) -> None`, `log_miss(key, start, end) -> None` (via `logging.getLogger("quant_agent.data.cache")`, INFO level)
  - `OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]` module constant, used by later provider tasks.

- [ ] **Step 1: Write the failing tests**

`tests/data/test_cache.py`:
```python
import logging
from datetime import datetime, timezone

import pandas as pd
import pytest

from quant_agent.data.cache import ParquetCache
from quant_agent.data.models import CacheKey


def make_df(rows):
    return pd.DataFrame(
        rows,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )


@pytest.fixture
def key():
    return CacheKey(source="yfinance", symbol="AAPL", interval="1d")


def test_get_coverage_none_when_no_file(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    assert cache.get_coverage(key) is None


def test_write_then_get_coverage(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    df = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100],
            [pd.Timestamp("2024-01-03", tz="UTC"), 1, 2, 0.5, 1.5, 100],
        ]
    )
    cache.write(key, df)
    coverage = cache.get_coverage(key)
    assert coverage == (pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2024-01-03", tz="UTC"))


def test_write_merges_and_dedupes(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    first = make_df([[pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100]])
    second = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 9, 9, 9, 9, 999],  # duplicate timestamp, should be replaced
            [pd.Timestamp("2024-01-02", tz="UTC"), 1, 2, 0.5, 1.5, 100],
        ]
    )
    cache.write(key, first)
    cache.write(key, second)
    full = cache.read(key, datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert len(full) == 2
    assert full.iloc[0]["open"] == 9  # later write wins on duplicate timestamp


def test_covers_true_when_range_fully_inside(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    df = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100],
            [pd.Timestamp("2024-01-10", tz="UTC"), 1, 2, 0.5, 1.5, 100],
        ]
    )
    cache.write(key, df)
    assert cache.covers(key, datetime(2024, 1, 2), datetime(2024, 1, 5)) is True


def test_covers_false_when_range_extends_beyond_cache(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    df = make_df([[pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100]])
    cache.write(key, df)
    assert cache.covers(key, datetime(2024, 1, 1), datetime(2024, 1, 5)) is False


def test_read_slices_to_requested_range(tmp_path, key):
    cache = ParquetCache(base_dir=str(tmp_path))
    df = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 2, 0.5, 1.5, 100],
            [pd.Timestamp("2024-01-05", tz="UTC"), 1, 2, 0.5, 1.5, 100],
            [pd.Timestamp("2024-01-10", tz="UTC"), 1, 2, 0.5, 1.5, 100],
        ]
    )
    cache.write(key, df)
    sliced = cache.read(key, datetime(2024, 1, 2), datetime(2024, 1, 6))
    assert list(sliced["timestamp"]) == [pd.Timestamp("2024-01-05", tz="UTC")]


def test_log_hit_emits_info_log(tmp_path, key, caplog):
    cache = ParquetCache(base_dir=str(tmp_path))
    with caplog.at_level(logging.INFO, logger="quant_agent.data.cache"):
        cache.log_hit(key, datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert "cache_hit" in caplog.text


def test_log_miss_emits_info_log(tmp_path, key, caplog):
    cache = ParquetCache(base_dir=str(tmp_path))
    with caplog.at_level(logging.INFO, logger="quant_agent.data.cache"):
        cache.log_miss(key, datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert "cache_miss" in caplog.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/data/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quant_agent.data.cache'`

- [ ] **Step 3: Write the implementation**

`src/quant_agent/data/cache.py`:
```python
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd

from .models import CacheKey

logger = logging.getLogger("quant_agent.data.cache")

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


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
        return cov_start <= pd.Timestamp(start, tz="UTC") and cov_end >= pd.Timestamp(end, tz="UTC")

    def read(self, key: CacheKey, start: datetime, end: datetime) -> pd.DataFrame:
        path = key.cache_path(self.base_dir)
        df = pd.read_parquet(path)
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")
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
```

Note on `test_write_merges_and_dedupes`: `keep="last"` in `drop_duplicates` means the most recently written row for a given timestamp wins, matching the assertion that `second`'s row (open=9) overwrites `first`'s row for the same timestamp.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/data/test_cache.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/quant_agent/data/cache.py tests/data/test_cache.py
git commit -m "feat: add ParquetCache with coverage-aware read/write and hit/miss logging"
```

---

### Task 4: Provider interface and error type

**Files:**
- Create: `src/quant_agent/data/providers/__init__.py`
- Create: `src/quant_agent/data/providers/base.py`
- Test: `tests/data/providers/__init__.py`
- Test: `tests/data/providers/test_base.py`

**Interfaces:**
- Produces: `MarketDataFetchError(Exception)`, `MarketDataProvider` ABC with `fetch(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame`. Tasks 5 and 6 subclass this.

- [ ] **Step 1: Write the failing test**

`tests/data/providers/__init__.py`:
```python
```

`tests/data/providers/test_base.py`:
```python
import pytest

from quant_agent.data.providers.base import MarketDataFetchError, MarketDataProvider


def test_market_data_provider_is_abstract():
    with pytest.raises(TypeError):
        MarketDataProvider()


def test_market_data_fetch_error_is_exception():
    assert issubclass(MarketDataFetchError, Exception)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/providers/test_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quant_agent.data.providers'`

- [ ] **Step 3: Write the implementation**

`src/quant_agent/data/providers/__init__.py`:
```python
```

`src/quant_agent/data/providers/base.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/providers/test_base.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/quant_agent/data/providers/__init__.py src/quant_agent/data/providers/base.py tests/data/providers
git commit -m "feat: add MarketDataProvider interface and MarketDataFetchError"
```

---

### Task 5: `YFinanceProvider`

**Files:**
- Create: `src/quant_agent/data/providers/yfinance_provider.py`
- Test: `tests/data/providers/test_yfinance_provider.py`

**Interfaces:**
- Consumes: `MarketDataProvider`, `MarketDataFetchError` from `quant_agent.data.providers.base` (Task 4).
- Produces: `YFinanceProvider` implementing `fetch(symbol, interval, start, end) -> pd.DataFrame` with the fixed OHLCV schema. Used by `MarketDataService` (Task 7).

- [ ] **Step 1: Write the failing tests**

`tests/data/providers/test_yfinance_provider.py`:
```python
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from quant_agent.data.providers.base import MarketDataFetchError
from quant_agent.data.providers.yfinance_provider import YFinanceProvider


def make_yf_raw():
    index = pd.to_datetime(["2024-01-01", "2024-01-02"])
    return pd.DataFrame(
        {
            "Open": [1.0, 2.0],
            "High": [1.5, 2.5],
            "Low": [0.5, 1.5],
            "Close": [1.2, 2.2],
            "Volume": [100, 200],
        },
        index=index,
    )


def test_fetch_normalizes_columns_and_schema():
    provider = YFinanceProvider()
    with patch("quant_agent.data.providers.yfinance_provider.yf.download", return_value=make_yf_raw()):
        df = provider.fetch("AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df["timestamp"].dt.tz is not None


def test_fetch_returns_empty_df_when_no_data():
    provider = YFinanceProvider()
    with patch("quant_agent.data.providers.yfinance_provider.yf.download", return_value=pd.DataFrame()):
        df = provider.fetch("AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert df.empty


def test_fetch_raises_market_data_fetch_error_on_exception():
    provider = YFinanceProvider()
    with patch("quant_agent.data.providers.yfinance_provider.yf.download", side_effect=RuntimeError("boom")):
        with pytest.raises(MarketDataFetchError):
            provider.fetch("AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/data/providers/test_yfinance_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quant_agent.data.providers.yfinance_provider'`

- [ ] **Step 3: Write the implementation**

`src/quant_agent/data/providers/yfinance_provider.py`:
```python
from __future__ import annotations

from datetime import datetime

import pandas as pd
import yfinance as yf

from .base import MarketDataFetchError, MarketDataProvider

_COLUMN_MAP = {
    "Date": "timestamp",
    "Datetime": "timestamp",
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/data/providers/test_yfinance_provider.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/quant_agent/data/providers/yfinance_provider.py tests/data/providers/test_yfinance_provider.py
git commit -m "feat: add YFinanceProvider"
```

---

### Task 6: `CCXTProvider`

**Files:**
- Create: `src/quant_agent/data/providers/ccxt_provider.py`
- Test: `tests/data/providers/test_ccxt_provider.py`

**Interfaces:**
- Consumes: `MarketDataProvider`, `MarketDataFetchError` from `quant_agent.data.providers.base` (Task 4).
- Produces: `CCXTProvider(exchange_id: str = "binance")` implementing `fetch(symbol, interval, start, end) -> pd.DataFrame` with the fixed OHLCV schema, paginating `fetch_ohlcv` until the range is covered. Used by `MarketDataService` (Task 7).

- [ ] **Step 1: Write the failing tests**

`tests/data/providers/test_ccxt_provider.py`:
```python
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from quant_agent.data.providers.base import MarketDataFetchError
from quant_agent.data.providers.ccxt_provider import CCXTProvider


def ms(dt):
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def test_fetch_normalizes_single_batch():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 2)
    batch = [
        [ms(datetime(2024, 1, 1)), 1.0, 1.5, 0.5, 1.2, 100],
        [ms(datetime(2024, 1, 2)), 2.0, 2.5, 1.5, 2.2, 200],
    ]
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.side_effect = [batch, []]

    with patch("quant_agent.data.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange
        provider = CCXTProvider(exchange_id="binance")
        df = provider.fetch("BTC/USDT", "1d", start, end)

    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df["timestamp"].dt.tz is not None


def test_fetch_returns_empty_df_when_no_data():
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = []

    with patch("quant_agent.data.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange
        provider = CCXTProvider(exchange_id="binance")
        df = provider.fetch("BTC/USDT", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))

    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert df.empty


def test_fetch_raises_market_data_fetch_error_on_exception():
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.side_effect = RuntimeError("boom")

    with patch("quant_agent.data.providers.ccxt_provider.ccxt") as mock_ccxt:
        mock_ccxt.binance.return_value = mock_exchange
        provider = CCXTProvider(exchange_id="binance")
        with pytest.raises(MarketDataFetchError):
            provider.fetch("BTC/USDT", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/data/providers/test_ccxt_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quant_agent.data.providers.ccxt_provider'`

- [ ] **Step 3: Write the implementation**

`src/quant_agent/data/providers/ccxt_provider.py`:
```python
from __future__ import annotations

from datetime import datetime, timezone

import ccxt
import pandas as pd

from .base import MarketDataFetchError, MarketDataProvider

_MS_PER_SECOND = 1000
_OUTPUT_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


class CCXTProvider(MarketDataProvider):
    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({"enableRateLimit": True})

    def fetch(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
        since = int(start.replace(tzinfo=timezone.utc).timestamp() * _MS_PER_SECOND)
        end_ms = int(end.replace(tzinfo=timezone.utc).timestamp() * _MS_PER_SECOND)
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
        except Exception as exc:
            raise MarketDataFetchError(
                f"ccxt fetch failed for {symbol} on {self.exchange_id}: {exc}"
            ) from exc

        if not rows:
            return pd.DataFrame(columns=_OUTPUT_COLUMNS)

        df = pd.DataFrame(rows, columns=_OUTPUT_COLUMNS)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")
        df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)]
        return df.reset_index(drop=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/data/providers/test_ccxt_provider.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/quant_agent/data/providers/ccxt_provider.py tests/data/providers/test_ccxt_provider.py
git commit -m "feat: add CCXTProvider"
```

---

### Task 7: `MarketDataService`

**Files:**
- Create: `src/quant_agent/data/market_data.py`
- Test: `tests/data/test_market_data.py`

**Interfaces:**
- Consumes: `ParquetCache` (Task 3), `CacheKey`/`Source` (Task 2), `MarketDataProvider` (Task 4), `YFinanceProvider` (Task 5), `CCXTProvider` (Task 6).
- Produces: `MarketDataService(cache: ParquetCache | None = None)` with `get(source, symbol, interval, start, end, exchange=None) -> pd.DataFrame` — the public entry point later sub-projects (strategy research) call.

- [ ] **Step 1: Write the failing tests**

`tests/data/test_market_data.py`:
```python
from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from quant_agent.data.cache import ParquetCache
from quant_agent.data.market_data import MarketDataService


def make_df(rows):
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


@pytest.fixture
def cache(tmp_path):
    return ParquetCache(base_dir=str(tmp_path))


def test_full_miss_fetches_and_caches(cache):
    service = MarketDataService(cache=cache)
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 1, 1, 1, 100],
            [pd.Timestamp("2024-01-02", tz="UTC"), 1, 1, 1, 1, 100],
        ]
    )
    service._providers["yfinance"] = mock_provider

    result = service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))

    mock_provider.fetch.assert_called_once_with("AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 2))
    assert len(result) == 2


def test_full_hit_does_not_call_provider(cache):
    service = MarketDataService(cache=cache)
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = make_df(
        [
            [pd.Timestamp("2024-01-01", tz="UTC"), 1, 1, 1, 1, 100],
            [pd.Timestamp("2024-01-05", tz="UTC"), 1, 1, 1, 1, 100],
        ]
    )
    service._providers["yfinance"] = mock_provider

    service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 1), datetime(2024, 1, 5))
    mock_provider.fetch.reset_mock()

    result = service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 2), datetime(2024, 1, 4))

    mock_provider.fetch.assert_not_called()
    assert len(result) == 0  # no rows exactly between 01-02 and 01-04 in the cached set, range still served from cache


def test_partial_miss_fetches_only_the_gap(cache):
    service = MarketDataService(cache=cache)
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = make_df(
        [[pd.Timestamp("2024-01-05", tz="UTC"), 1, 1, 1, 1, 100],
         [pd.Timestamp("2024-01-10", tz="UTC"), 1, 1, 1, 1, 100]]
    )
    service._providers["yfinance"] = mock_provider
    service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 5), datetime(2024, 1, 10))
    mock_provider.fetch.reset_mock()

    mock_provider.fetch.return_value = make_df(
        [[pd.Timestamp("2024-01-12", tz="UTC"), 2, 2, 2, 2, 200]]
    )

    result = service.get("yfinance", "AAPL", "1d", datetime(2024, 1, 5), datetime(2024, 1, 12))

    mock_provider.fetch.assert_called_once_with("AAPL", "1d", pd.Timestamp("2024-01-10", tz="UTC").to_pydatetime(), datetime(2024, 1, 12))
    assert len(result) == 3


def test_ccxt_source_uses_exchange_specific_provider(cache):
    service = MarketDataService(cache=cache)
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = make_df(
        [[pd.Timestamp("2024-01-01", tz="UTC"), 1, 1, 1, 1, 100]]
    )
    service._ccxt_providers["binance"] = mock_provider

    result = service.get(
        "ccxt", "BTC/USDT", "1h", datetime(2024, 1, 1), datetime(2024, 1, 1), exchange="binance"
    )

    mock_provider.fetch.assert_called_once()
    assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/data/test_market_data.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'quant_agent.data.market_data'`

- [ ] **Step 3: Write the implementation**

`src/quant_agent/data/market_data.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/data/test_market_data.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full unit test suite**

Run: `uv run pytest -v`
Expected: PASS, all tests green, `integration`-marked tests skipped/deselected

- [ ] **Step 6: Commit**

```bash
git add src/quant_agent/data/market_data.py tests/data/test_market_data.py
git commit -m "feat: add MarketDataService with gap-only cache-backed fetching"
```

---

### Task 8: Integration tests against real APIs

**Files:**
- Create: `tests/data/providers/test_providers_integration.py`

**Interfaces:**
- Consumes: `YFinanceProvider` (Task 5), `CCXTProvider` (Task 6). No production code produced — this task only adds tests.

- [ ] **Step 1: Write the integration tests**

`tests/data/providers/test_providers_integration.py`:
```python
from datetime import datetime, timedelta

import pytest

from quant_agent.data.providers.ccxt_provider import CCXTProvider
from quant_agent.data.providers.yfinance_provider import YFinanceProvider


@pytest.mark.integration
def test_yfinance_provider_fetches_real_data():
    provider = YFinanceProvider()
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    df = provider.fetch("AAPL", "1d", start, end)
    assert not df.empty
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]


@pytest.mark.integration
def test_ccxt_provider_fetches_real_data():
    provider = CCXTProvider(exchange_id="binance")
    end = datetime.utcnow()
    start = end - timedelta(days=1)
    df = provider.fetch("BTC/USDT", "1h", start, end)
    assert not df.empty
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
```

- [ ] **Step 2: Run the integration tests manually (real network)**

Run: `uv run pytest tests/data/providers/test_providers_integration.py -m integration -v`
Expected: PASS (2 tests) — requires internet access

- [ ] **Step 3: Confirm default run still excludes them**

Run: `uv run pytest -v`
Expected: integration tests not collected/run, all other tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/data/providers/test_providers_integration.py
git commit -m "test: add integration tests for real yfinance/ccxt fetches"
```

---

## Self-Review Notes

- **Spec coverage:** repo scaffold (Task 1), `CacheKey`/schema (Task 2), `ParquetCache` coverage+merge+hit/miss logging (Task 3), provider ABC (Task 4), yfinance provider (Task 5), ccxt provider (Task 6), `MarketDataService` gap-only fetch orchestration (Task 7), integration tests (Task 8) — every spec section has a task.
- **Gap-only fetching:** Task 7 implements true two-sided gap fetch (before cache start, after cache end) rather than a full refetch, matching the spec's "fetch the missing sub-range(s) only" requirement exactly.
- **Type/signature consistency:** `MarketDataService.get()` signature, `ParquetCache` method names, and `CacheKey` fields are used identically across Tasks 3, 5, 6, 7 — checked against each task's Interfaces block.
