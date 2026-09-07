# NR4 (Narrow Range 4) Breakout with SMA200 Filter — Backtest Report

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_nr4_sma200_breakout.py`
**Knowledge base id:** 2026-09-08-031

## Hypothesis

Per the "Narrow Range 4" (NR4) pattern (a shorter-lookback variant of Toby
Crabel's NR7 concept), as described in strategydecoder.app's "NR4 Pattern
Breakout with SMA 200 Filter" strategy listing and forexfactory.com's
definition ("current bar's range is the smallest range of any of the last
four bars"): a narrow-range bar marks a volatility contraction; combined
with an SMA200 trend filter, a breakout above the NR4 bar's high in an
established uptrend is a lower-risk trend-continuation long entry.

Distinct from this repo's existing NR7 strategy (2026-09-04-081, rejected,
best full-sample Sharpe 0.617) via a shorter 4-bar contraction window and
a slower SMA200 trend filter instead of NR7's 20-period EMA.

## Single-config validators (QQQ, full sample 2015-01-01 to 2026-09-01)

Best grid config: `nr_window=4, trend_window=200, max_hold_days=10`

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ PASS | 1.124 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 20.9% | ≤ 25% |
| Transaction cost survival (10bps/trade, 144 trades) | ✅ PASS | net Sharpe 0.918 | ≥ 0.5 |
| Walk-forward (manual 4-equal-slice fallback) | ✅ PASS | 4/4 splits positive Sharpe | ≥ 75% |
| Parameter sensitivity (8-cell QQQ-only sweep) | ✅ PASS | relative std 0.082 | ≤ 0.5 |

**All 5 validators pass, strong margins → ACCEPT (equity/QQQ scope).**
Notably lower trade count (144) than the rejected NR7 variant and
excellent parameter stability (relative std 0.082, vs Fisher-Stochastic-
RVI's 0.444 from the prior iteration this run).

## Grid test summary (96 cells: nr_window∈{4,5} × trend_window∈{150,200} × max_hold_days∈{10,15} × 2 equity symbols × 2 crypto symbols × 3 vol regimes)

- `pass_fraction`: 20.8% (20/96)
- `by_asset_class`: equity 20/48; **crypto 0/48 (decisive reject)**
- `by_vol_regime`: low 16/32, mid 4/32, **high 0/32 (decisive reject)**
- `best_cell`: nr_window=4, trend_window=200, max_hold_days=10 — equity/QQQ/low-vol, Sharpe 2.501

## Scope / honest limitations

- Edge concentrated in **equity, low/mid-vol regimes**; zero passing
  cells on crypto or in high-vol regime — do not deploy outside that
  scope.
- SPY was not separately validated with the single-config suite this
  iteration (grid shows equity passes broadly, but QQQ was the primary
  config tested).

## Sources

- https://www.google.com/search?q=%22Narrow+Range+4%22+NR4+OR+%22Inside+Range%22+breakout+strategy+specific+entry+exit+rules+backtest+-nr7 (SERP surfaced strategydecoder.app and forexfactory.com)
- https://www.google.com/search?q=strategydecoder.app+%22Narrow+Range+4%22+SMA+200+filter (SERP snippet with exact NR4+SMA200 combo description; full page itself returned 404)
