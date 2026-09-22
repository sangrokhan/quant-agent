# Backtest Report: SPY RSI(3) Pullback / Prior-Day-High Rebound Exit

**Strategy file:** `strategies/2026-09-22_spy_rsi3_priorday_high_rebound.py`
**Date:** 2026-09-22
**Outcome:** ACCEPTED (equity only, scope noted below)

## Hypothesis

Per QuantifiedStrategies.com's X/Twitter thread "AI Found a Profitable SPY
Strategy in 30 Seconds. Then We Tried to Break It."
(https://x.com/QuantifiedStrat/article/2101677169235652639, read via
browser_exec — `web_extract` cannot render X.com article pages), a simple
long-only pullback strategy: entry when close > 200-day SMA (uptrend intact)
AND RSI(3) < 20 (short-term oversold), buy next open; exit at the next open
after close first exceeds the PRIOR day's high (rebound confirmation, not a
fixed RSI-level or MA-recross exit). No stop-loss/profit-target, one
position at a time. Source's own extensive robustness claims (full
1993-2026 SPY sample: 253 trades, 75.9% win rate, PF 2.60; survived
RSI-length/threshold sweeps, MA-length sweeps, alternate exits, 20bps
costs, 4 market eras) are independently re-checked here on our own data/
validator pipeline rather than trusted at face value.

Distinct from this repo's existing RSI-mean-reversion family: the exit
rule (close > prior day's high) had 0 prior matches in
`strategies_index.jsonl` (vs. existing SMA(5)-recovery exit and RSI-level
exit variants).

## Step 6 — Grid test summary

Grid: `rsi_window` ∈ {3,4}, `entry_threshold` ∈ {20,25}, `trend_window`=200
× symbols {QQQ, SPY} (equity) / {BTC/USDT, ETH/USDT} (crypto) × 3 vol-regime
terciles = 48 cells, 2019-01-01 to 2026-09-01.

```
pass_fraction: 0.2708 (13/48)
by_asset_class: equity 13/24 passed, crypto 0/24 passed
by_vol_regime:  low 7/16, mid 4/16, high 2/16   (passes across ALL regimes, unlike prior DiNapoli attempt)
best_cell: rsi_window=3, entry_threshold=20, SPY, low-vol regime, Sharpe=1.85
worst_cell: rsi_window=4, entry_threshold=25, QQQ, mid-vol regime, Sharpe=-0.84
```

Edge is equity-specific (crypto fails outright, consistent with the
source's SPY-only design and long-uptrend-pullback rationale not
transferring to crypto's different regime structure), but unlike the
prior DiNapoli-stochastic attempt this iteration, the pass fraction spans
all three vol regimes (not concentrated in one slice only).

## Step 7 — Full-sample validators (best config: SPY, rsi_window=3,
entry_threshold=20, trend_window=200, full sample 2019-2026)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.232 | >= 1.0 | PASS |
| Max drawdown | 8.11% | <= 25% | PASS |
| Transaction cost survival (10 bps/trade, 62 trades) | 1.013 net Sharpe | >= 0.5 | PASS |
| Walk-forward (manual 4-split; `vbt.utils.splitting.RangeSplitter` AttributeError, known repo-wide gap) | 4/4 splits positive (1.0) | >= 0.75 | PASS |
| Parameter sensitivity (4-point grid: rsi_window×entry_threshold, relative std) | 0.136 | <= 0.5 | PASS |

All five validators pass on the full 2019-2026 sample, not just a
favorable regime slice — the grid's low-vol-only best cell (Sharpe 1.85)
and the full-sample result (Sharpe 1.23) are directionally consistent
(unlike the prior DiNapoli attempt where the grid cell's edge evaporated
full-sample).

## Step 8 — Decision: ACCEPTED

Scope: equity only (SPY confirmed; QQQ untested at this exact config but
same asset class showed some passing cells in the grid). Crypto is
explicitly OUT OF SCOPE — decisively fails across all vol regimes in the
grid, consistent with the strategy's design rationale (long-term-uptrend
pullback dip-buying) not obviously transferring to crypto's price
dynamics. Kept as a live strategy in `strategies/`.

## Source

https://x.com/QuantifiedStrat/article/2101677169235652639
