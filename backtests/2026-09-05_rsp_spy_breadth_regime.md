# RSP/SPY Market-Breadth Regime Filter — Backtest Report

**Hypothesis:** RSP/SPY ratio (equal-weight vs cap-weight S&P 500) trend
(SMA rising vs falling) is a market-breadth proxy: rising = broad
participation/healthy rally (long), falling = narrow mega-cap-concentrated
rally/fragile market (flat).

**Source:** web search results (web_search backend failing this session,
used browser_exec Google fallback) surfacing commentary e.g. "RSP/SPY
Ratio Hits 5-Year Low, Warning Signs for Investors" -- "Breadth matters.
Sustained bull markets typically see this ratio rising, not falling. A
narrow rally is a fragile one." No single authoritative backtest source
found (article link itself 404'd); this is implemented from the general
market-commentary rationale, tested mechanically rather than replicating
a specific published backtest.

**Strategy file:** `strategies/2026-09-05_rsp_spy_breadth_regime.py`

## Step 6 — Grid test summary (param_grid: sma_window in [10,20,50] x
slope_window in [10,20,50]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 108, passed_cells: 15, **pass_fraction: 0.139** -- weak
  from the start.
- by_asset_class: equity 15/54 (28%), crypto 0/54 (0%).
- by_vol_regime: low 12/36, mid 0/36, high 3/36.
- best_cell: sma_window=10, slope_window=20, QQQ, low-vol regime,
  Sharpe=1.83 (single tercile, not full period).

## Step 7 — Single-config validators (best grid config over FULL period:
sma_window=10, slope_window=20)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL 0.470 | FAIL 0.441 |
| Max Drawdown (<= 0.25) | FAIL 0.359 | FAIL 0.284 |

Decisive failure on both full-period Sharpe and MDD for both symbols --
did not proceed to transaction-cost/parameter-sensitivity checks given the
primary metrics already fail clearly.

## Outcome: **REJECTED**

The RSP/SPY breadth-trend signal does not produce a full-period edge;
grid pass_fraction (0.139) was already the weakest of this session's
five strategies, and the "best" grid cell's Sharpe=1.83 was an artifact of
a single low-vol tercile slice, not representative of the whole backtest
window (full-period Sharpe collapses to ~0.45-0.47). A short-window SMA
slope on a ratio that itself trends for years (as sector
concentration/mega-cap dominance evolves slowly) produces too much noise
relative to signal at daily granularity; a longer-horizon/monthly version
of this idea might fare differently but is out of scope for this
iteration. Crypto again fails completely (0/54).
