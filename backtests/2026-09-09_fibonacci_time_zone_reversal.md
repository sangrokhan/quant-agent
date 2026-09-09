# Fibonacci Time Zone Reversal — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_fibonacci_time_zone_reversal.py`
**Outcome:** REJECTED

## Hypothesis

Per https://fxnx.com (Google AI-overview synthesis of Fibonacci Time Zone
guides, FXNX/Fusion Markets/TradingView sources): vertical lines projected
at Fibonacci-sequence day-count offsets (1,2,3,5,8,13,21,34,55,89,144,...)
from a major swing-low anchor mark statistically favored reversal
"turning windows." Source's exact rule: anchor at swing extreme, wait for
price within a 1-2 bar window of a projected time-zone line, require a
reversal candle confirming, enter on confirmation, stop past the
immediate swing extreme (here ATR-multiple approximation), exit on
time-invalidation or profit target at the next time-zone line
(approximated with a max_hold_days time-stop).

First Fibonacci Time Zone (day-count projection) strategy in this repo —
distinct from Fibonacci retracement/extension (price-ratio, not
time-based).

## Single-config validation (best grid cell config: swing_window=10,
tolerance_days=2, max_hold_days=10, atr_mult=2.0, atr_window=14)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.555 (FAIL, thr 1.0) | 47.7% (FAIL, thr 25%) | 0.411 (FAIL, thr 0.5) | 1.0/1.0 (PASS) | 0.294 (PASS, thr 0.5) |
| SPY | 0.369 (FAIL, thr 1.0) | 38.3% (FAIL, thr 25%) | 0.190 (FAIL, thr 0.5) | 1.0/1.0 (PASS) | 1.35 (FAIL, thr 0.5) |

Full sample fails on Sharpe, max drawdown, and transaction-cost survival
for both QQQ and SPY. Only walk-forward passes cleanly (each quarter-slice
individually has positive Sharpe, since the strategy trades often and
rarely loses badly on any *one* slice, but the aggregate full-sample
Sharpe is too low and drawdown too deep).

## Grid summary (swing_window=[10,20,30] x tolerance_days=[1,2] x
max_hold_days=[10,20], equity=[QQQ,SPY] x crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 144, passed_cells: 22, pass_fraction: 0.153
- by_asset_class: equity 22/72 (0.306), crypto 0/72 (0.0 — decisive fail)
- by_vol_regime: low 17/48 (0.354), mid 5/48 (0.104), high 0/48 (0.0)
- best_cell: swing_window=10/tolerance_days=2/max_hold_days=10, QQQ
  low-vol regime, Sharpe 2.18
- worst_cell: swing_window=30/tolerance_days=2/max_hold_days=20, SPY
  mid-vol regime, Sharpe -0.56

The edge (where it exists at all) is concentrated almost entirely in the
low-vol regime slice on equities; it evaporates in mid/high-vol regimes
and fails decisively on all crypto cells. Even the grid's best-cell
config, when validated on the FULL sample (not just the low-vol slice),
fails Sharpe/MDD/TC — the grid's regime-sliced Sharpe was optimistic
because it only measured performance during the favorable low-vol
subperiod, not the whole backtest window including drawdowns.

## Verdict: REJECTED

All three headline validators (Sharpe, MDD, transaction-cost survival)
fail on the full sample for both equity symbols tested; crypto rejected
decisively (0/72 grid cells). Time-based Fibonacci projections (day-count
windows with no price-level constraint) appear to be too weak a signal on
their own — the "reversal candle" confirmation used here (simple up-close
bar) fires far too often (~185 trades over ~8.7 years, i.e. roughly every
17 trading days) to be a meaningfully selective entry filter, which
likely explains both the high drawdown (frequent low-quality entries) and
the transaction-cost drag.

**Note for future loops:** if revisiting, a much stricter reversal
confirmation (e.g. a true engulfing/pin-bar pattern per the source's
"Candlestick Confirmation" rule, rather than a plain up-close bar) or a
tighter `tolerance_days=0` (exact time-zone hit only, not +/-1-2 day
window) might reduce trade frequency and improve selectivity — worth a
follow-up with a stricter confirmation filter rather than abandoning the
Fibonacci-time-projection concept outright.
