# Backtest Report: Donchian Volume-Z-Score Breakout

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_donchian_volume_zscore_breakout.py`
**KB id:** 2026-09-20-093

## Hypothesis

Per QuanterLab's "Volume Confirmation in Breakouts"
(https://quanterlab.com/articles/breakout-volume-confirmation, read via
browser_exec this iteration): breakout hit rates improve 10-20 points when
the breakout bar's volume is in the top quartile of its recent rolling
distribution. The source explicitly proposes a statistical Volume Z-Score
formalization (Z = (volume - rolling mean) / rolling std, Z > 2.0 flags
"statistically unusual" volume) as an alternative to a fixed RVOL ratio
threshold, because it re-calibrates to the current volume *regime*'s
dispersion rather than just its level.

This repo has tested several volume-confirmed Donchian/breakout variants
(RVOL ratio 2026-09-04-166, OBV-breakout 2026-09-05-060, volume-multiple +
candle-quality 2026-09-10-123, VROC 2026-09-12-140, ATR-filter
2026-09-11-032, Livermore pivotal-point 2026-09-12-168) all landing as
near-misses (Sharpe 0.6-1.0) but none used a genuine statistical Z-score
gate. This iteration tests that specific missing variant.

## Grid test summary (channel_window x [15,20,30], z_threshold x
[1.5,2.0,2.5], max_hold_days x [10,15]; QQQ/SPY/BTC-USDT/ETH-USDT;
vol_regime_splits=3; 2019-01-01 to 2026-09-01)

- Total cells: 216, passed: 87, pass_fraction: 0.403
- By asset class: equity 24/108 (0.222), crypto 63/108 (0.583)
- By vol regime: low 53/72 (0.736), mid 23/72 (0.319), high 11/72 (0.153)
- Best cell: crypto ETH/USDT, channel_window=15/z_threshold=2.5/max_hold_days=15,
  mid-vol tercile, Sharpe 1.984
- Worst cell: equity SPY, channel_window=30/z_threshold=1.5/max_hold_days=10,
  mid-vol tercile, Sharpe -1.051

Notably crypto edges out equity in this grid (unusual for this repo, where
volume-confirmation breakout gates have typically favored equity) -- but the
signal is concentrated almost entirely in the low-vol tercile broadly, and
even the best full-sample configs (below) fall well short of the Sharpe
threshold.

## Full-sample single-config scan (4 promising grid configs x 4 symbols)

| Symbol | channel_window | z_threshold | max_hold_days | Full-sample Sharpe |
|---|---|---|---|---|
| QQQ | 15 | 2.5 | 15 | 0.315 |
| QQQ | 20 | 2.0 | 15 | 0.427 |
| QQQ | 15 | 2.0 | 10 | 0.391 |
| QQQ | 20 | 2.5 | 10 | **0.429** (best QQQ) |
| SPY | 15 | 2.5 | 15 | -0.116 |
| SPY | 20 | 2.0 | 15 | 0.180 |
| SPY | 15 | 2.0 | 10 | -0.152 |
| SPY | 20 | 2.5 | 10 | -0.175 |
| BTC/USDT | 15 | 2.5 | 15 | 0.246 |
| BTC/USDT | 20 | 2.0 | 15 | 0.268 |
| BTC/USDT | 15 | 2.0 | 10 | 0.243 |
| BTC/USDT | 20 | 2.5 | 10 | 0.286 |
| ETH/USDT | 15 | 2.5 | 15 | 0.280 |
| ETH/USDT | 20 | 2.0 | 15 | 0.271 |
| ETH/USDT | 15 | 2.0 | 10 | 0.265 |
| ETH/USDT | 20 | 2.5 | 10 | **0.304** (best ETH) |

Grid-cell Sharpes (per vol-regime tercile) reach 1.98 in narrow slices, but
no symbol clears Sharpe>=1.0 on the full sample at any tested config -- the
grid's "pass_fraction" is driven by a handful of favorable low-vol/mid-vol
sub-periods rather than a robust full-sample edge.

## Single-config validator suite (best QQQ config: channel_window=20,
z_threshold=2.5, max_hold_days=10)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **FAIL** | value=0.429, threshold=1.0 |
| Max drawdown | PASS | value=0.0386, threshold=0.25 |

Walk-forward and transaction-cost-survival were skipped -- the primary
Sharpe validator already fails decisively (0.43 vs 1.0 required), so
running the full suite would not change the accept/reject decision
(per RESEARCH_LOOP.md Step 7, run the subset relevant to the workload; a
decisive full-sample Sharpe failure is sufficient grounds for rejection
without further validator spend).

## Decision: REJECTED

Full-sample Sharpe fails decisively on every symbol/config tested despite a
0.40 grid pass_fraction concentrated in low-vol regime slices. The Z-score
volume-confirmation construction does not produce a materially better edge
than the RVOL-ratio/OBV/VROC variants already tested and rejected in this
repo -- confirms this general breakout-plus-volume-confirmation family is
saturated regardless of the specific volume-statistic formalization used.
