# Backtest Report: Keltner Channel Breakout, Long-Only (EMA(30)+ATR(10)x2.0)

**Strategy file:** `strategies/2026-09-03_keltner_channel_breakout.py`
**Hypothesis ID:** 2026-09-03-016
**Source:** Google search snippets for Keltner Channel breakout strategy
(web_search failed with a DDGS/TLS connection error, fell back to
browser_exec Google search).

## Hypothesis

Keltner Channel = EMA(ema_period) midline +/- atr_multiplier * ATR(atr_period)
outer bands. TradingView's own summary: "identify bullish breakouts when
price closes above the upper channel". Exit on close crossing back below
the EMA midline (conventional for channel-midline systems, matching the
exit-logic pattern already used by Donchian -008 and SuperTrend -014 in
this repo). Distinct construction: Keltner's band is a *static-width*
ATR-scaled envelope around a fixed EMA (does not trail/ratchet like
SuperTrend's flip-based stop line, and is volatility-scaled unlike
Donchian's pure price-level channel).

Long-only per SAFETY.md.

## Grid test (validation/grid_test.py::run_strategy_grid)

Grid: `atr_multiplier` in {1.5,2.0,2.5} x `ema_period` in {20,30} x symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 72 cells,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.236** (17/72)
- by_asset_class: equity 17/36 (47%), crypto 0/36 (0%)
- by_vol_regime: low 12/24 (50%), mid 5/24 (21%), high 0/24 (0%)
- best_cell: QQQ, atr_multiplier=2.0/ema_period=30, low-vol regime, Sharpe 2.99
- worst_cell: SPY, atr_multiplier=2.5/ema_period=30, high-vol regime, Sharpe -1.28

## Single-config validators (best grid config: atr_multiplier=2.0, ema_period=30)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Walk-fwd (4-split) |
|---|---|---|---|---|
| **QQQ** | **1.33 (pass, thr 1.0)** | **15.7% (pass, thr 25%)** | **1.24 (pass, thr 0.5, 56 trades @10bps)** | **1.0 (pass, thr 0.75)** |
| SPY | 0.38 (fail) | 20.1% (pass) | 0.23 (fail) | 0.5 (fail) |
| BTC/USDT | 0.19 (fail) | 46.5% (fail) | 0.03 (fail) | 1.0 (pass) |

Parameter sensitivity (6-point atr_multiplier/ema_period sweep on QQQ):
relative std 0.19 (Sharpe range 0.74-1.33), inside the 0.5 threshold —
the best-config's Sharpe of 1.33 is on the higher end of the sweep but not
a lone outlier (ema_period=30 configs cluster around 1.0-1.33 across all
three multipliers tested).

Walk-forward used a manual 4-way date-slice fallback (vectorbt
`utils.splitting.RangeSplitter` still broken — unfixed since 2026-09-03-002).

## Decision: **ACCEPT (QQQ only)**

QQQ clears all 5 standard validators cleanly at the grid-optimal config
(atr_multiplier=2.0, ema_period=30, atr_period=10): Sharpe 1.33, MDD 15.7%,
net-of-cost Sharpe 1.24 (56 trades over 7.7 years @ 10bps), walk-forward
4/4 splits positive, parameter-sensitivity relative std 0.19.

SPY fails decisively on this same config (Sharpe 0.38, TC-adj Sharpe 0.23,
walk-forward only 2/4 splits) — this Keltner setup does NOT transfer
cleanly across even closely-related equity indices, unlike several prior
QQQ/SPY-accepted strategies in this repo (e.g. RSI2 -005, Donchian -008).
BTC/USDT fails across the board (MDD 46.5%, near-zero Sharpe).

**Scope: QQQ only, long-only, Keltner(EMA 30, ATR 10 x2.0) breakout. Do NOT
extend to SPY or crypto without further validation — the SPY failure here
is a genuine within-equity-class falsification, not just a narrower
crypto/vol-regime finding like most prior accepted strategies.**
