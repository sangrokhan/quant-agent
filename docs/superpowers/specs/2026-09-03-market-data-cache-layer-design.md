# Market Data Cache Layer — Design Spec

Status: approved
Date: 2026-09-03
Sub-project 1 of the quant-agent autonomous research system (see `~/.hermes/plans/quant-agent-seed.yaml` for the full-system goal).

## Purpose

Provide a repo scaffold and a local-first market data access layer that both stock (yfinance) and crypto (ccxt) sources go through. This is the foundation every later sub-project (strategy research, validation, paper trading) builds on. The seed plan's hard constraint this sub-project must satisfy: **no duplicate external API calls for the same symbol/interval/date-range — always check the local cache first, only call the API for what's missing.**

## Scope

In scope:
- Repo scaffold: `pyproject.toml` (uv-managed), `src/` layout, `.gitignore`, `.env.example`
- `MarketDataProvider` interface with two implementations: yfinance (stocks) and ccxt (crypto, default exchange binance)
- Parquet-backed local cache with coverage-aware fetch (only fetch the missing date range, merge into existing cache)
- Cache hit/miss logging
- pytest unit tests (mocked), with a small set of `@pytest.mark.integration` tests that hit real network, excluded from default runs

Out of scope (future sub-projects):
- Strategy research/codegen/validation pipeline
- Knowledge base / novelty check
- Paper trading simulation engine
- Ralph loop orchestration, usage budget management, Hermes cron wiring
- Slack notifications
- CI (GitHub Actions) — deferred to the orchestration sub-project

## Repo Layout

```
quant-agent/
  pyproject.toml
  .env.example
  .gitignore                    # excludes data/cache/
  src/quant_agent/
    data/
      models.py                 # CacheKey, OHLCVRequest dataclasses
      cache.py                  # ParquetCache
      providers/
        base.py                 # MarketDataProvider ABC
        yfinance_provider.py
        ccxt_provider.py
      market_data.py            # MarketDataService — public entry point
  tests/
    data/
      test_cache.py
      test_market_data.py
      test_providers_integration.py
```

## Data Model

`CacheKey`: `(source: Literal["yfinance", "ccxt"], exchange: str | None, symbol: str, interval: str)`.
- `exchange` is `None` for yfinance, e.g. `"binance"` for ccxt.
- `symbol` is stored normalized (yfinance ticker as-is, e.g. `"AAPL"`; ccxt pair as-is, e.g. `"BTC/USDT"`), sanitized for filesystem use when building the cache path (`/` → `_`).

Cache file path: `data/cache/{source}/{exchange or "_"}/{symbol_sanitized}/{interval}.parquet`

OHLCV schema (fixed, all providers normalize to this before caching):
`timestamp (UTC, tz-aware), open, close, high, low, volume`

## Components

**`MarketDataProvider` (ABC, `providers/base.py`)**
```python
def fetch(self, symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame
```
Returns a DataFrame in the fixed OHLCV schema for exactly the requested range. Raises on failure — no silent partial results.

**`YFinanceProvider`** — wraps `yfinance.download`, normalizes columns/index to the fixed schema.

**`CCXTProvider`** — takes `exchange_id` (default `"binance"`), wraps `ccxt.<exchange>().fetch_ohlcv`, paginates as needed to cover the requested range, normalizes to the fixed schema.

**`ParquetCache` (`data/cache.py`)**
- `get_coverage(key: CacheKey) -> DateRange | None` — reads the parquet file's min/max timestamp if it exists.
- `read(key: CacheKey, start, end) -> pd.DataFrame` — slices the cached parquet for the requested range.
- `write(key: CacheKey, df: pd.DataFrame) -> None` — merges new rows into the existing parquet (dedupe on `timestamp`, sort), writes back.
- Logs a `cache_hit` or `cache_miss` (with the fetched sub-range) event on every access, so cache hit ratio is inspectable from logs.

**`MarketDataService` (`data/market_data.py`)** — the only entry point other sub-projects should use:
```python
def get(self, source, symbol, interval, start, end, exchange=None) -> pd.DataFrame
```
Flow:
1. Build `CacheKey`, check `ParquetCache.get_coverage`.
2. If the cached range fully covers `[start, end]` → return `cache.read(...)`, log hit.
3. Else → call the matching provider's `fetch()` for the *missing* sub-range(s) only, `cache.write()` the result, log miss, then return `cache.read(...)` for the full requested range.

Provider selection: a small dict/factory in `MarketDataService.__init__` mapping `source → provider instance`.

## Error Handling

- Provider `fetch()` failures propagate as exceptions (typed, e.g. `MarketDataFetchError`) — no retry logic here. Retry/backoff belongs to the future Ralph loop orchestration layer, not this sub-project.
- If the requested range isn't fully cached, the service always attempts a fetch for the gap — it never silently returns a partial/stale result for a range it wasn't asked to cover.

## Testing

- `test_cache.py`: unit tests for `ParquetCache` coverage detection, merge/dedupe on write, hit/miss logging — using in-memory/mock DataFrames, no real files needed beyond pytest `tmp_path`.
- `test_market_data.py`: unit tests for `MarketDataService.get()` branching (full hit / full miss / partial miss), with `YFinanceProvider`/`CCXTProvider` mocked out.
- `test_providers_integration.py`: a handful of tests marked `@pytest.mark.integration` that call the real yfinance/ccxt APIs for one small known symbol/range each, to catch upstream schema drift. Excluded from default `pytest` runs (`pytest -m "not integration"` as default via `pyproject.toml` config); run manually with `pytest -m integration`.

## Tooling

- `uv` for dependency/environment management (`pyproject.toml`, `uv.lock`)
- Dependencies: `yfinance`, `ccxt`, `pandas`, `pyarrow` (parquet), `pytest`
- No CI in this sub-project (deferred to orchestration sub-project)

## Open Questions

None — all resolved during brainstorming (uv, parquet, stocks+crypto together, pytest-only with mocked-by-default network tests).
