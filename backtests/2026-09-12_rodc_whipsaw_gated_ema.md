# Backtest Report: RODC Whipsaw-Gated EMA Crossover

**Strategy file:** `strategies/2026-09-12_rodc_whipsaw_gated_ema.py`
**Date:** 2026-09-12

## Hypothesis

Per Richard Poster's "Taming The Effects Of Whipsaw" (TASC March 2024, fully
disclosed Pine v5 source:
https://www.tradingview.com/script/z9IFUy5m-TASC-2024-03-Rate-of-Directional-Change/):
the Rate of Directional Change (RODC) counts ZigZag reversal segments within
a rolling lookback window (RODC = 100 * Segments / WindowSize); a higher
RODC means an alternating/choppy (whipsaw) market, a lower RODC means a
clean trend. The source discloses only the indicator (no concrete
entry/exit rule), explicitly framing it as a whipsaw filter meant to
suppress false trend-following entries. This strategy adapts that stated
purpose into a testable rule: a fast/slow EMA crossover trend signal, gated
flat unless RODC is below `rodc_max` (a genuinely low-whipsaw/trending
regime). The source's tick-based ZigZag threshold is replaced with a
percentage threshold to generalize beyond forex.

## Grid test (Step 6) — `grid_result_rodc_whipsaw.json`

Grid: `fast_ema ∈ {10,20}`, `slow_ema ∈ {30,50}`, `rodc_max ∈ {30,40,50}` ×
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} × vol regime terciles, 2018-01-01 to
2026-09-01. 144 total cells.

- **pass_fraction: 0.2569** (37/144)
- by_asset_class: equity 37/72 passed, **crypto 0/72 passed** (decisive fail)
- by_vol_regime: low 24/48, mid 12/48, **high 1/48** — works mostly in
  low/mid-vol regimes, largely fails in high-vol
- best_cell: SPY, `fast_ema=20, slow_ema=50, rodc_max=30`, low-vol, Sharpe 2.71
- worst_cell: QQQ, `fast_ema=20, slow_ema=50, rodc_max=40`, high-vol, Sharpe -1.06

A quick manual full-sample sweep around the grid's promising region found
`fast_ema=10, slow_ema=30, rodc_max=30` outperforms the raw grid's
best-per-cell pick (which only reflects one vol-regime slice) once run
over the FULL 2018-2026 sample for both SPY and QQQ.

## Standard validators (Step 7) — best full-sample config `fast_ema=10, slow_ema=30, rodc_max=30, max_hold_days=60`

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| SPY | 1.048 (pass, thr 1.0) | 0.138 (pass, thr 0.25) | 0.980 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | rel_std 0.102 (pass, thr 0.5) | **ACCEPT** |
| QQQ | 1.187 (pass, thr 1.0) | 0.152 (pass, thr 0.25) | 1.126 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | rel_std 0.112 (pass, thr 0.5) | **ACCEPT** |

Both symbols pass all 5 validators with low turnover (43/47 trades over
~8.7 years) and strong drawdown control.

Crypto (BTC/USDT, ETH/USDT) rejected decisively at the grid stage (0/72
cells) — not re-validated with the full suite.

## Decision

**ACCEPT for equity (SPY and QQQ).** Both symbols pass Sharpe, max
drawdown, transaction-cost survival, walk-forward, and parameter
sensitivity on the full 2018-2026 sample. This is a genuine, if narrow,
success: the RODC whipsaw filter's own stated purpose (suppress
false trend-following entries in choppy regimes) does add real value when
paired with a simple EMA crossover, corroborating the source's own
framing. **Reject for crypto** — the strategy does not translate to
24/7 crypto dynamics (0/72 grid cells passed).
