# Backtest Report: Santa Claus Rally calendar effect (2026-09-05)

**Hypothesis:** US equities tend to rally during the last 5 trading days of
December plus the first 2 trading days of January (the classic Santa Claus
Rally window, Stock Trader's Almanac-popularized). Long-only, calendar-based
strategy with no price signal at all.

**Source:** Wikipedia/Britannica Santa Claus Rally definition;
quantifiedstrategies.com's own backtest headline cited (CAGR ~0.7% while
only invested ~2.3% of the time, over a longer historical sample than
tested here).

**Novelty:** distinct from the already-tested broader Halloween/Sell-in-May
seasonal strategy (2026-09-04-104, a 6-month Nov-Apr hold), a much narrower
~7-trading-day annual window.

## Grid test (validation/grid_test.py)

- param_grid: `december_trading_days` in {5, 7}, `january_trading_days` in
  {2, 3}
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits = 3
- total_cells = 48, passed_cells = 0, **pass_fraction = 0.0%** (decisive,
  no cell passes in any asset class or vol regime)
- best_cell: SPY, december_trading_days=7, january_trading_days=3,
  low-vol regime, Sharpe 0.95 (still below the 1.0 threshold)

## Single-config validators (config: december_trading_days=5,
january_trading_days=2, the classic definition, full 2019-01-01..2026-09-01
sample, ~7 occurrences of the window)

| Symbol | Sharpe | MDD | Trades |
|---|---|---|---|
| QQQ | -0.428 (FAIL, decisive) | 0.147 (PASS) | 7 |
| SPY | -0.127 (FAIL, decisive) | 0.068 (PASS) | 7 |

## Decision: REJECTED (decisive, 0/48 grid cells)

Over this repo's 2019-2026 sample window, the Santa Claus Rally effect does
not hold — both QQQ and SPY post negative Sharpe over the ~7 annual
occurrences of the window (only 7 trading years in the sample), and no
grid cell (across the two lookback-window variants tested, in any asset
class or vol regime) clears the 1.0 Sharpe bar. This is consistent with the
effect being a relatively small, historically-documented but statistically
thin edge (the source's own headline CAGR of only 0.7% while invested 2.3%
of the time over a much longer historical sample) that does not
consistently materialize in a shorter recent 7.5-year window, and/or with
the specific 2019-2026 period containing enough adverse Dec/Jan
observations (e.g. Dec 2018 hangover effects excluded, but 2021-2022 and
2024-2025 volatility) to overwhelm the effect. Crypto (with no
institutional light-volume mechanism) unsurprisingly also fails.
