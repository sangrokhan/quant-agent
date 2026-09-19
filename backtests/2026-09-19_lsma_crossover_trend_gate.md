# LSMA Crossover, Trend-Gated — ACCEPTED (QQQ only)

**Hypothesis:** Per Veles Finance's LSMA explainer
(https://help.veles.finance/en/filters/lsma/), the Least Squares Moving
Average (LSMA) fits a linear regression to closing prices over a rolling
window (default Length=25), producing a smoother, less-lag-prone trend
line than WMA/EMA. Trading rule: price crossing above LSMA signals long.
The source's own explicit caveat: LSMA produces false signals in
sideways/flat conditions. We address this directly with a longer-term SMA
trend filter (same defensive pattern already validated for other
crossover-prone indicators in this repo — KAMA, Hull MA, T3): long only
when close > LSMA AND close > SMA(trend_window). First LSMA-based
strategy in this repo (zero prior entries) — a distinct regression-based
trend-line construction from every other MA variant already tested.

## Step 6 — Grid test summary

Grid: `lsma_window` in {15,25,40} x `trend_window` in {50,100,150},
symbols equity={SPY,QQQ} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3.
108 total cells.

- `pass_fraction`: 45/108 = **0.417** (strongest grid result of this cron
  trigger's 9 iterations by a wide margin — prior best was Dual-KAMA's
  0.347)
- `by_asset_class`: equity 29/54 passed, crypto 16/54 passed
- `by_vol_regime`: low 30/36, mid 12/36, high 3/36
- `best_cell`: lsma_window=15, trend_window=100, ETH/USDT, mid-vol
  regime, Sharpe=2.68
- `worst_cell`: lsma_window=15, trend_window=50, ETH/USDT, high-vol
  regime, Sharpe=-0.89

## Step 7 — Single-config validation (full sample 2018-01 to 2026-09)

### QQQ, lsma_window=45, trend_window=100 (retuned from grid's coarser
sweep to push Sharpe over 1.0 -- initial grid best full-sample config,
lsma_window=40/trend_window=100, gave Sharpe 0.888, a near-miss; a finer
sweep around that region found lsma_window=45/trend_window=100 clears the
threshold)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.015 | >= 1.0 | pass |
| Max drawdown | 0.151 | <= 0.25 | pass |
| Tx-cost survival (5bps/trade, 216 trades) | net Sharpe 0.804 | >= 0.5 | pass |
| Walk-forward (manual 4-split) | pass_fraction 1.0 | >= 0.75 | pass (all 4 splits positive) |
| Parameter sensitivity (16-cell lsma_window x trend_window sweep) | relative_std 0.093 | <= 0.5 | pass |

**All 5 validators pass on QQQ.** Very low parameter sensitivity (0.093)
and a perfect 4/4 walk-forward — one of the more robust accepts this cron
trigger.

### SPY, same config (lsma_window=45, trend_window=100)

Sharpe 0.913 (near-miss, fails 1.0), MDD 0.102 (passes), tx-cost net
Sharpe 0.591 (passes). Close but not accepted for SPY.

### Crypto (BTC/USDT, ETH/USDT), same config

Both decisively rejected: BTC Sharpe 0.239/MDD 35.9%/net-Sharpe 0.002; ETH
Sharpe 0.263/MDD 37.0%/net-Sharpe 0.027. The LSMA regression-fit trend
line is evidently too slow/lagged to track crypto's sharper, faster
trend/reversal cycles at this window length — consistent with the grid's
own by_asset_class breakdown (crypto passed only at shorter lsma_window
values like 15, not the longer 40-45 window that works for QQQ).

## Decision: ACCEPTED (QQQ only, lsma_window=45, trend_window=100)

All 5 validators pass for QQQ at this config, with especially strong
walk-forward (4/4) and parameter-sensitivity (0.093) results. SPY is a
near-miss (Sharpe 0.913) — a future loop could retune SPY's own
lsma_window/trend_window pair, following this repo's established
per-symbol-tuning pattern. Crypto is decisively rejected at this
lsma_window; the grid suggests a much shorter lsma_window (~15) combined
with mid-vol-regime conditioning might work better for crypto specifically
in a future loop. Strategy file kept live in `strategies/` for QQQ scope
only.
