# Extreme-Day-Rank Mean Reversion (QQQ)

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_extreme_day_rank_reversal.py`
**KB id:** 2026-09-23-049

## Hypothesis

Per Quantpedia's "Automated Trading Edge Analysis"
(https://quantpedia.com/automated-trading-edge-analysis), the simplest
tested trading edge with a clear positive result: go long the next day if
today's return is among the 25 lowest of the trailing 250 trading days.
Source explicitly notes the short-side mirror (highest returns) only
works in bear markets -- this strategy is long-only per that distinction.
Adds a close>SMA(200) uptrend gate (not in the source) and a fixed
hold_days exit (source doesn't disclose an explicit exit rule beyond "go
long the next day").

## Grid test (Step 6)

108 cells: `n_extreme`[15,25,35] x `hold_days`[3,5,10] x
{QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol regimes (2019-01-01 to 2026-09-01).

- **pass_fraction:** 0.213 (23/108)
- **by_asset_class:** equity 22/54, crypto 1/54 (decisive fail)
- **by_vol_regime:** low 18/36, mid 3/36, high 2/36
- **best_cell:** n_extreme=35, hold_days=10, QQQ, low-vol, Sharpe=2.701

## Single-config validation (Step 7) -- n_extreme=25, hold_days=10,
lookback=250, trend_window=200

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | 1.063 (pass) | 1.026 (pass) |
| Max Drawdown | 12.3% (pass, thr 25%) | 14.5% (pass) |
| Net Sharpe after 10bps costs | 0.966 (pass, thr 0.5) | 0.905 (pass) |
| Walk-forward (4-split manual) | 0.75 (pass, thr 0.75) | 0.75 (pass) |
| Parameter sensitivity (9-combo) | 0.357 (pass, thr 0.5) | **0.551 (fail)** |
| num_trades | 57 | 53 |

## Decision

**Accept QQQ only.** All 5 validators pass for QQQ. SPY fails parameter
sensitivity (relative std 0.551 > 0.5 threshold) despite passing
Sharpe/MDD/TC/walk-forward -- the edge on SPY is less stable across nearby
parameter values, so reject SPY per the standard rule (all validators must
pass). Crypto decisively rejected in the grid (1/54).

## Source

https://quantpedia.com/automated-trading-edge-analysis
