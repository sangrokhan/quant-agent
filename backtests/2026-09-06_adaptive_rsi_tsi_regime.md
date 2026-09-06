# Backtest Report: Adaptive RSI/TSI Regime-Gated Mean Reversion

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_adaptive_rsi_tsi_regime.py`
**Status:** REJECTED (grid decisively negative)

## Hypothesis
TSI (True Strength Index, double-smoothed momentum oscillator) gates RSI(14)
oversold-cross entries: deeper RSI oversold threshold required when TSI
indicates a trending regime (|TSI| > threshold), shallower threshold when
range-bound. Long only when TSI >= 0 (never buy dips in a confirmed
downtrend). Exit on RSI > 60, TSI < 0, or max hold days.

Source: Google AI-overview synthesis of TradingView/IG/Quantified Strategies
articles on adaptive RSI+TSI hybrid systems (queried 2026-09-06, page:
`https://www.google.com/search?q=relative+strength+index+RSI+trend+strength+index+TSI+adaptive+strategy+rules+backtest`).

## Grid Test (Step 6)

- `param_grid`: `tsi_trend_threshold` in [8.0, 15.0], `rsi_oversold_trend` in
  [20.0, 25.0, 30.0]
- `symbols`: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- `vol_regime_splits`: 3 (low/mid/high realized-vol terciles)
- Period: 2019-01-01 to 2026-09-01

**Result: 0/72 cells passed (pass_fraction = 0.0)**

- By asset class: equity 0/36, crypto 0/36 — fails uniformly, no
  asset-class-specific edge.
- By vol regime: low 0/24, mid 0/24, high 0/24 — fails uniformly across
  every volatility regime.
- Best cell: crypto ETH/USDT, high-vol regime, tsi_trend_threshold=15.0,
  rsi_oversold_trend=20.0 → Sharpe 0.204 (still below the 1.0 pass
  threshold).
- Worst cell: equity QQQ, high-vol regime, same params → Sharpe -0.758.

## Decision
**Rejected at the grid stage.** The grid result (0/72, uniformly failing
across both asset classes and all three vol regimes) is decisive enough
that a further single-config validator suite (Sharpe/MDD/walk-forward/TC
survival) would not change the accept/reject outcome — every cell already
misses the Sharpe >= 1.0 bar by a wide margin, including the best cell at
0.20. Per `suggested_workload=max` guidance, a full grid was run (2
asset classes x 3 vol regimes x 6 param combos), which is itself the basis
for skipping the redundant single-config validator pass.

## Notes for future iterations
The TSI regime gate (adaptive RSI threshold widening/narrowing) does not by
itself rescue RSI mean-reversion entries — the long-only TSI>=0 filter may
be too restrictive (misses reversals right at trend inflection, which is
often the strongest mean-reversion opportunity), or the RSI cross-back-above
trigger combined with a trend-strength gate is simply redundant with signals
already tested and rejected in this repo (see `2026-09-03-019` RSI
divergence, `2026-09-05-053` Laguerre RSI mean-reversion). A future revisit
could try TSI as a *short-entry* enabler (fade RSI overbought when TSI<0)
rather than only gating longs, or drop the long-only constraint entirely.
