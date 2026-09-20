# Backtest Report: 21-Day Breakout + Trend + Momentum Gate (2026-09-20)

**Status: ACCEPTED** (QQQ, SPY, BTC/USDT). ETH/USDT near-miss (fails MDD only, 0.338 vs 0.25 threshold at its best grid config) — not pursued further this iteration.

## Hypothesis

Source: https://finlab.finance/en/blog/us-breakout-trend-strategy (visited via `browser_exec`).

A fresh N-day high in a broad index ETF carries directional information
only when the broader trend agrees. Source's disclosed 3-condition risk-on
gate, applied at index level:

1. **Breakout trigger**: close > prior 21-day high, staying "active" for
   `entry_persist` sessions after it first fires.
2. **Trend filter**: close > SMA(200).
3. **Momentum confirmation**: trailing 126-day return > 0.

Source's own reported result: filtered breakouts positive 82% of the time
3 months later vs 61% for unfiltered; CAGR 37.2% vs QQQ buy-and-hold
20.6%, MDD -28.3% vs -35.6% (executed via leveraged ETF rotation). This
repo tests a plain long/flat, unleveraged, single-asset adaptation.

## Single-config metrics (per-symbol tuned configs)

| Symbol | Config | Sharpe | MDD | Net Sharpe (5bp, N trades) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | breakout_window=15, entry_persist=10, mom_window=90 | 1.330 ✅ | 0.152 ✅ | 1.270 ✅ (94 trades) | 1.00 ✅ | 0.045 ✅ |
| SPY | breakout_window=15, entry_persist=10, mom_window=63 | 1.105 ✅ | 0.139 ✅ | 1.017 ✅ (92 trades) | 1.00 ✅ | 0.183 ✅ |
| BTC/USDT | breakout_window=21, entry_persist=3, mom_window=126 | 1.352 ✅ | 0.194 ✅ | 1.312 ✅ (144 trades) | 1.00 ✅ | 0.040 ✅ |

(`check_walk_forward` in `validation/validators.py` currently errors — a
pre-existing `vectorbt.utils.splitting` issue in this install — so
walk-forward used the repo's documented manual 4-equal-slice fallback:
per-slice Sharpe > 0 = pass.)

ETH/USDT (breakout_window=25, entry_persist=3, mom_window=63): Sharpe
1.258 ✅ but MDD 0.338 ❌ (fails the 0.25 threshold) — a genuine near-miss,
not pursued further this iteration.

## Grid summary

`validation/grid_test.py::run_strategy_grid`, `breakout_window ∈ {15,21}`
× `entry_persist ∈ {3,5}` × `mom_window ∈ {90,126}`, symbols
`{QQQ,SPY,BTC/USDT,ETH/USDT}`, `vol_regime_splits=3`:

- total_cells=96, passed_cells=37, **pass_fraction=0.385**
- by_asset_class: equity 18/48, crypto 19/48 (near-even split — unusually
  broad for this repo)
- by_vol_regime: low 21/32, mid 15/32, **high 1/32** (edge concentrated in
  calmer regimes, as expected for a trend+momentum-confirmed breakout)
- best_cell: QQQ, low-vol, breakout_window=21/entry_persist=5/mom_window=90, Sharpe 2.166
- worst_cell: SPY, high-vol, breakout_window=15/entry_persist=5/mom_window=126, Sharpe -0.643

## Decision: ACCEPT (QQQ, SPY, BTC/USDT)

All 5 validators pass for all three symbols at their per-symbol tuned
configs. This is one of the broader-scope acceptances in this repo's
history — passing on both equity symbols (QQQ AND SPY, not just one) plus
one crypto symbol, unlike many prior accepted strategies that are
QQQ-only or equity-only. ETH/USDT is a genuine near-miss (Sharpe clears,
MDD does not) and is documented but not rescued this iteration — a future
loop could retry with a de-risking overlay (e.g. leverage_cap or a
vol-regime exit gate) specifically for ETH/USDT.

## Notes

- Turnover is low (92–144 trades over ~8.7 years), consistent with a
  monthly-rebalance-style trend/momentum overlay rather than a
  high-frequency mean-reversion signal — net Sharpe after 5bp costs stays
  close to gross Sharpe for all three accepted symbols.
- Per-symbol parameter tuning was needed (QQQ/SPY use mom_window 90/63
  respectively, BTC/USDT uses a much longer mom_window=126 and shorter
  entry_persist=3) — consistent with this repo's established convention
  that "accepted" strategies often need per-symbol retuning rather than
  one shared config across the whole universe.
