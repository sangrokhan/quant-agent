# Volume-Weighted MACD (VWMACD) Histogram Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-155 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_vwmacd_hist_sizing_sma_trend.py`

## Hypothesis

Volume-Weighted MACD (VWMACD, Buff Dormeier's amendment to Appel's MACD;
per Optuma/thinkorswim/LuxAlgo): `VWMACD_line = VWMA_fast - VWMA_slow`
(volume-weighted moving averages instead of EMAs), `signal = EMA(line,
signal_span)`, `hist = line - signal`. Repo has 4 prior VWMACD entries, all
binary signal-line-crossover triggers. This iteration reframes the VWMACD
histogram (already zero-centered, no diff/roc needed) as a continuous
sizing dial: rolling z-scored + tanh-squashed to [-1,+1], sized within an
SMA(trend_window) uptrend gate, deadband + leverage_cap for crypto. First
VWMACD continuous-sizing variant.

Source: https://www.optuma.com/kb/tools/volume/volume-weighted-macd/
(via web_search, cross-referenced with thinkorswim/LuxAlgo descriptions).

## Grid test summary (Step 6)

`param_grid={fast_window: [10,12], slow_window: [26,35], sensitivity:
[0.5,0.7]}`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto),
vol_regime_splits=3.

- **total_cells:** 96, **passed:** 50, **pass_fraction:** 0.521.
- **by_asset_class:** equity 25/48 (0.521), crypto 25/48 (0.521) — evenly
  split, unusual symmetry this cron trigger.
- **by_vol_regime:** low 32/32 (1.0, ALL low-vol cells pass), mid 9/32
  (0.281), high 9/32 (0.281).
- **best_cell:** QQQ, fast_window=12/slow_window=35/sensitivity=0.5,
  low-vol, Sharpe 2.71.
- **worst_cell:** SPY, fast_window=12/slow_window=26/sensitivity=0.7,
  mid-vol, Sharpe -0.41.

## Single-config validator results (Step 7)

Best grid config (fast_window=12, slow_window=35, sensitivity=0.5) tested
per symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Trades | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | 226 | 1.043 (pass) | 0.103 (pass) | 0.416 (**fail**, thr 0.5, near-miss) | 1.0 (pass) | 0.057 (pass) | **rejected** |
| SPY | 204 | 0.957 (**fail**, near-miss) | 0.073 (pass) | 0.282 (**fail**, thr 0.5) | 1.0 (pass) | 0.073 (pass) | **rejected** |
| BTC/USDT | 149 | 1.631 (pass) | 0.189 (pass) | 1.409 (pass) | 1.0 (pass) | 0.090 (pass) | **accepted** |
| ETH/USDT | 153 | 1.342 (pass) | 0.232 (pass) | 1.191 (pass) | 1.0 (pass) | 0.043 (pass) | **accepted** |

## Decision

**Accepted (crypto only):** BTC/USDT, ETH/USDT — all 5 validators pass with
strong margins.
**Rejected (equity):** QQQ (near-miss on TC-survival only, gross Sharpe and
all else pass), SPY (near-miss on both Sharpe and TC-survival). Consistent
with this cron trigger's recurring pattern: continuous sizing overlays on
slower-turnover volume/momentum indicators tend to survive equity
transaction costs better than fast ones, and VWMACD at these settings still
trades too often (204-226 trades) for the edge to survive costs on equity
daily bars.

Scope note: this VWMACD histogram continuous-sizing dial only holds up on
crypto (BTC/ETH) at leverage_cap=0.4; QQQ is a genuine near-miss (TC-survival
only) worth revisiting with a wider deadband or slower fast/slow pair in a
future iteration.

Full raw grid: `/tmp/vwmacd_grid_summary.json` (not committed, ephemeral).
Full raw validators: `validators_vwmacd_hist_sizing.json`.
