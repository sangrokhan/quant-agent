# Backtest Report: Chande's TrendScore, Oversold-to-Bullish Zero-Cross

**Strategy file:** `strategies/2026-09-12_chande_trendscore_oversold_cross.py` (REJECTED — kept as rejected-attempt record)
**Date:** 2026-09-12
**Source:** Tushar Chande, Stocks & Commodities (Sep 1993), via https://theforexgeek.com/trend-score-indicator/ and https://www.tradingpedia.com/forex-trading-indicators/chandes-trendscore/

## Hypothesis

TrendScore (sign-count of current close vs each of the previous `lookback`
closes, scaled to -10..+10 range) crossing from oversold (<-5) back above
zero signals a long entry, per the source's own disclosed rule: "If the
blue line...rises above the zero signal line from the oversold zone (below
the -5 level), you may go long...cancel your buy orders if the blue line
falls below the 5 level during a bullish trend." First Chande TrendScore
strategy in this repo (distinct from Qstick, CMO, Dynamic Momentum Index,
VIDYA already tested).

## Step 6 — Grid test summary

Grid: `lookback` in [10,20,30] x `confirm_window` in [5,10,15], symbols
equity=[QQQ,SPY] / crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3 (108 cells).

```
total_cells: 108, passed_cells: 26, pass_fraction: 0.241
by_asset_class: equity 26/54 passed; crypto 0/54 (decisive reject)
by_vol_regime:  low 11/36; mid 5/36; high 10/36  (best spread across regimes of any strategy tested this cron trigger)
best_cell: lookback=20, confirm_window=5, QQQ, low-vol, Sharpe=2.15
worst_cell: lookback=20, confirm_window=5, SPY, mid-vol, Sharpe=-0.33
```

## Step 7 — Single-config validation (best grid config: lookback=20, confirm_window=5, oversold=-5, overbought=5, max_hold_days=20)

Full 2018-01-01..2026-09-01 sample:

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 1.132 PASS | 0.825 FAIL | >= 1.0 |
| Max Drawdown | 0.197 PASS | 0.150 PASS | <= 0.25 |
| TC survival (10bps/trade) | 1.047 PASS | 0.725 PASS | net Sharpe >= 0.5 |
| Walk-forward (4-split) | 1.00 PASS | 1.00 PASS | >= 0.75 |
| Param sensitivity (rel std) | **FAIL (degenerate)** | **FAIL (degenerate)** | <= 0.5 |

Param-sensitivity detail: sweeping `lookback` in [10,20,30] revealed
`lookback=10` produces Sharpe=inf on QQQ (extremely thin/degenerate trade
sample at that short lookback — likely near-zero-variance single-trade
outcome), which blows up the relative-std computation to NaN/Infinity.
This is a genuine finding, not a computation bug: the strategy's behavior
is unstable/degenerate at short lookbacks, so it fails the parameter
sensitivity check on both symbols even though the source's own default
(lookback=20) performs well in isolation.

## Step 8 — Decision: **REJECT**

QQQ is a near-miss: passes Sharpe, MDD, TC survival, and walk-forward
(4/5 validators), but fails parameter sensitivity due to a degenerate,
unstable configuration at lookback=10 that produces an inf-Sharpe outlier
— this instability means the strategy's live performance is fragile to
the exact lookback chosen, so per Step 8's "accept only if ALL validators
pass" rule, QQQ is rejected. SPY additionally fails the primary Sharpe
threshold outright (0.825 < 1.0). Crypto rejected decisively (0/54 grid
cells). Notably this had the best cross-regime distribution of any strategy
tested this cron trigger (passes span low/mid/high vol, not concentrated in
one regime) — worth revisiting with a tighter/floor-guarded lookback grid
(e.g. excluding lookback<=15) in a future iteration if this angle is
revisited.
