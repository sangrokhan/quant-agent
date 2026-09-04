# Relative Vigor Index (RVI) signal-line crossover at extremes — backtest report

**Strategy file:** `strategies/2026-09-04_rvi_signalcross_extremes.py`
**Hypothesis id:** 2026-09-04-130

## Hypothesis

The Relative Vigor Index (close-open momentum normalized by trading range,
4-bar weighted-smoothed numerator/denominator, then n-period SMA) with a
4-bar-weighted signal line. Per
[quantifiedstrategies.com](https://www.quantifiedstrategies.com/relative-vigor-index/):
crossovers of RVI above/below its signal line "at the extreme ends of the
indicator's usual range" signal momentum shifts. Operationalized here as:
long entry when RVI crosses above signal AND RVI < -0.2 (oversold zone);
exit on RVI crossing below signal or a max_hold_days time-stop.

Source: https://www.quantifiedstrategies.com/relative-vigor-index/ (via
browser_exec Google-search fallback after web_search's DDGS/Yahoo backend
returned a connection error).

## Grid summary (Step 6)

`period` in {10,14} x `entry_threshold` in {0.1,0.2} x `max_hold_days`
in {10,15}, symbols QQQ/SPY/BTC/USDT/ETH/USDT, vol_regime_splits=3:

- 96 cells total, 9 passed (pass_fraction=0.094)
- by_asset_class: equity 9/48, crypto 0/48
- by_vol_regime: low 0/32, mid 5/32, high 4/32
- best_cell: period=10, entry_threshold=0.2, max_hold_days=10, QQQ, mid-vol, Sharpe=1.87
- worst_cell: period=14, entry_threshold=0.2, max_hold_days=10, SPY, low-vol, Sharpe=-1.20

## Primary config validators (period=10, entry_threshold=0.2, max_hold_days=10)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.614 **FAIL** | -0.075 **FAIL** |
| Max drawdown (<=0.25) | 0.259 **FAIL** | 0.345 **FAIL** |
| Net Sharpe after costs (>=0.5, 10bps/trade) | 0.550 PASS (30 trades) | -0.120 **FAIL** (28 trades) |

Walk-forward / parameter-sensitivity skipped: primary Sharpe and MDD both
already fail decisively on both symbols and the low grid pass_fraction
(9.4%, and notably 0/32 in the low-vol regime -- the opposite pattern from
most other rejected strategies in this log which usually pass low-vol
cells) doesn't justify the additional compute.

## Decision

**Reject (both QQQ and SPY).** MDD fails on both (0.259 QQQ, 0.345 SPY,
both over the 0.25 threshold), Sharpe fails on both, and SPY additionally
fails TC-survival. Crypto rejected outright (0/48 grid cells).
