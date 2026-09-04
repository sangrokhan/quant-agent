# Backtest Report: Rolling-Swing-Low Anchored VWAP Crossover

**Strategy file:** `strategies/2026-09-04_anchored_vwap_swinglow.py`
**Hypothesis id:** 2026-09-04-138
**Source:** https://trendspider.com/learning-center/anchored-vwap/

## Hypothesis

Anchored VWAP (AVWAP) computes a cumulative volume-weighted average price
from a significant anchor point (swing low, trend reversal) instead of
session start, reflecting the average cost basis of everyone who has
traded since that point. Per trendspider.com's own description of the
mechanic (a discretionary support/resistance tool, no single fixed
numeric rule given), this repo operationalizes it mechanically:
re-anchor whenever a new rolling `lookback`-day lowest-low is confirmed,
accumulate VWAP from that anchor forward, and trade the crossover of
close vs. the anchored VWAP (long on cross above, exit on cross below or
a max_hold_days time-stop). First VWAP-family (volume-weighted, not just
price-weighted) strategy tested in this repo.

## Single-config validators (QQQ, lookback=20, max_hold_days=30 -- Step 6 grid's best low-vol cell config)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full period) | ❌ (near-miss) | 0.836 | ≥ 1.0 |
| max_drawdown | ❌ (near-miss) | 0.298 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 175 trades) | ✅ | net Sharpe 0.651 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` still broken in this install) | ✅ | 3/4 splits positive Sharpe | ≥ 0.75 pass fraction |
| parameter_sensitivity | ✅ | relative std 0.106 (4-combo grid) | ≤ 0.5 |

## Step 6 grid summary

`param_grid={lookback:[20,40], max_hold_days:[30,60]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
48 cells total.

- **pass_fraction:** 0.188 (9/48)
- **by_asset_class:** equity 9/24 passed (38%); crypto 0/24 passed (0%)
- **by_vol_regime:** low 8/16; mid 1/16; high 0/16
- **best_cell:** lookback=20, max_hold_days=30, QQQ, low-vol regime, Sharpe 2.80
- **worst_cell:** lookback=20, max_hold_days=60, SPY, mid-vol regime, Sharpe -0.37

## Decision: REJECT (near-miss)

Two of five validators fail, both narrowly: Sharpe 0.836 vs 1.0
threshold, and MDD 0.298 vs 0.25 threshold. TC-survival, walk-forward,
and param-sensitivity all pass cleanly, and the strategy generates a
healthy 175 trades over the full period (not overfit to a handful of
lucky entries). Consistent with the general pattern seen this run: the
edge is equity-only and concentrated in low-vol regimes (crypto
decisively 0/24; mid/high vol equity mostly fails). Worth a future
revisit with a tighter MDD control (e.g. a vol-regime gate restricting
entries to low/mid-vol conditions, or a stop-loss overlay) since the
underlying signal quality (positive Sharpe, stable across param grid,
decent walk-forward) is more promising than most of this run's other
rejects.
