# Backtest Report: Dual-EMA + RSI-Midline Confirmation, Low-Vol Regime Gate (REJECTED)

**Strategy file:** `strategies/2026-09-08_ema_rsi_midline_volgate.py`
**Date:** 2026-09-08
**Knowledge base id:** 2026-09-08-169

## Hypothesis

Direct follow-up to near-miss `2026-09-04-165` (dual-EMA(20/50) crossover +
RSI(14)>50 midline confirmation, QQQ full-sample Sharpe 0.930 near-miss,
MDD/TC-survival/param-sensitivity all pass; grid pass distribution 13/32 low,
9/32 mid, 1/32 high — LESS concentrated than the same-trigger's Range Filter
[DW] fix, 36/18/1). Tests whether the same entry-only low-vol regime gate
(20d realized vol <= trailing 252d median) that rescued Range Filter [DW]
(2026-09-08-168) also rescues this near-miss.

## Grid summary (Step 6)

`fast_span` in [10, 20] x `slow_span` in [50, 100] x `max_hold_days` in
[20, 30] x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 96 cells.

- pass_fraction: 0.167 (16/96)
- by_asset_class: equity 16/48, crypto 0/48
- by_vol_regime: low 16/32 (0.50), mid 0/32, high 0/32
- best_cell: QQQ, fast_span=10/slow_span=50/max_hold_days=30, low-vol, Sharpe 2.54
- best full-sample-avg config: QQQ fast_span=10/slow_span=50/max_hold_days=30 (avg regime Sharpe 0.78)

## Single-config validation (Step 7): QQQ, fast_span=10, slow_span=50, max_hold_days=30

- Sharpe: 0.828 (FAIL, threshold 1.0) — WORSE than the original ungated
  near-miss (0.930).
- Max drawdown: 0.128 (pass)
- SPY: Sharpe 0.435 (decisive fail, worse than original 0.208... actually
  slightly better than 0.208 but still decisively failing)

## Decision: REJECTED

Unlike the Range Filter [DW] fix earlier this cron trigger (which rescued a
near-miss from 0.957 to 1.0047), the low-vol gate here made QQQ's Sharpe
*worse* (0.930 -> 0.828), not better. The original strategy's edge was more
evenly spread across vol regimes (13/9/1 across low/mid/high) than Range
Filter [DW]'s edge was (36/18/1) — removing mid-vol trades here cut into
genuinely profitable trades rather than removing whipsaw losses. This
confirms the fix pattern (regime-gate a near-miss) is NOT universally
applicable — it only helps when the grid's regime concentration is sharply
skewed toward one regime (as with Range Filter [DW] and, per the ASI
swing-channel precedent 2026-09-08-097, sometimes not even then). Consistent
with the ASI swing-channel finding (2026-09-08-097, also rejected after
gating): a genuinely weak base edge, or one whose edge isn't concentrated in
low-vol specifically, cannot be rescued by this fix.
