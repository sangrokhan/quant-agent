# Backtest Report: Dual-EMA Trend-Filtered Moving Average Envelope Breakout

**Strategy file:** `strategies/2026-09-06_ema_trend_envelope_breakout.py`
**Date:** 2026-09-06

## Hypothesis

Long entry when 20-EMA > 50-EMA (trend filter) AND close crosses above a
20-day-SMA-based envelope band (2% shift); exit on close crossing back
below the baseline SMA, the trend filter breaking, or a time-stop. Per a
Google AI-overview synthesis (queried "Envelope channel dual moving
average breakout strategy specific numeric rules ATR"). Distinct from
this repo's already-rejected plain Moving Average Envelope
mean-reversion strategy (2026-09-04-065, buys on LOWER band touch, no
trend filter) via the opposite trigger direction (upper-band breakout)
and an added dual-EMA trend-alignment gate.

## Grid test (Step 6)

`param_grid`: envelope_pct in {0.015,0.02,0.03}, fast_span in {10,20},
max_hold_days in {20,30}; symbols equity=[QQQ,SPY],
crypto=[BTC/USDT,ETH/USDT]; vol_regime_splits=3. 144 total cells.

- pass_fraction: 0.1667 (24/144)
- by_asset_class: equity 24/72, crypto 0/72
- by_vol_regime: low 22/48, mid 2/48, high 0/48
- best_cell (tercile-level): envelope_pct=0.015, fast_span=20,
  max_hold_days=20, QQQ, low-vol, Sharpe 2.590

## Full-sample manual scan (Step 6/7)

Expanded scan (envelope_pct in {0.01,0.015,0.02,0.03}, fast_span in
{10,20}, max_hold_days in {15,20,25,30}, filtered to >=10 trades) on
QQQ and SPY full-sample. **Best full-sample Sharpe found: QQQ 0.970
(envelope_pct=0.03, fast_span=10, max_hold_days=20, 39 trades); SPY only
0.691** — neither symbol clears the 1.0 Sharpe threshold at any tested
config. Tercile-level grid best-cells are again a narrow low-vol-regime
artifact that doesn't generalize to full-sample performance, consistent
with the pattern seen in most of this repo's rejected strategies.

Crypto rejected decisively (0/72 grid cells).

## Decision: **REJECT**

Full-sample Sharpe fails the 1.0 threshold on both QQQ (best 0.970) and
SPY (best 0.691) across the entire parameter space tested. Skipped
single-config validator suite (MDD/tx-cost/walk-forward/param-sensitivity)
given the decisive full-sample Sharpe failure — no config clears the
primary gate.
