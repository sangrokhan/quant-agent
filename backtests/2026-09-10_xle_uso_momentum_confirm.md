# 2026-09-10 — XLE Trend-Following Gated by USO Momentum Confirmation (REJECTED)

## Hypothesis

Energy-sector equities (XLE) are driven by crude oil prices; USO (direct
crude exposure) is the faster/leading leg while XLE dampens/lags the same
move per multiple comparison articles (no single disclosed numeric rule
found). Self-constructed, fully disclosed strategy: SMA trend-following on
XLE gated by USO's own trailing momentum being positive (cross-asset
confirmation).

Strategy file: `strategies/2026-09-10_xle_uso_momentum_confirm.py`

## Parameter sweep (trend_window x mom_window, XLE, max_hold_days=30)

| trend_window | mom_window=10 | mom_window=20 | mom_window=40 |
|---|---|---|---|
| 30 | 0.330 | 0.571 | 0.228 |
| 50 | 0.211 | 0.585 | 0.280 |
| 100 | -0.125 | 0.255 | 0.014 |

Best Sharpe found: 0.585 (trend_window=50, mom_window=20) — nowhere near
the 1.0 threshold, and max drawdown (0.278) at that config would also
narrowly pass, but Sharpe alone already disqualifies this.

## Decision: REJECT

No parameter combination approaches Sharpe 1.0. The USO-momentum
confirmation gate doesn't meaningfully improve on a plain XLE SMA
trend-follower (which is itself a well-worn, unremarkable strategy already
represented in spirit by many SMA-based strategies in this repo) — full
validator suite/grid test skipped as unnecessary given the decisive
sweep result.
