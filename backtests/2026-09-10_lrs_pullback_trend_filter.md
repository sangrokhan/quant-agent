# 2026-09-10 — Linear Regression Slope Pullback + SMA Trend Filter (REJECTED, QQQ near-miss)

## Hypothesis

Per https://www.quantifiedstrategies.com/linear-regression-slope/: Linear
Regression Slope (LRS) is the rate-of-change of a least-squares regression
line fit to closing prices over a short lookback (source example: 5 days).
Source's own disclosed backtest on SPY: buying when the slope turns negative
(pullback) and exiting after a fixed N-day hold performed best at N=9 (avg
gain 0.39%/trade) but was "not particularly good" vs buy-and-hold
unconditionally. This iteration's novel addition: gate the source's own
negative-slope pullback entry with an SMA(trend_window=200) uptrend filter
(buy dips only within an established uptrend), testing whether that
sharpens the source's own weak unconditional edge.

Strategy file: `strategies/2026-09-10_lrs_pullback_trend_filter.py`

## Grid summary (slope_window in [5,10,20] x hold_days in [5,9,15], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- 15/108 cells passed (pass_fraction 0.139), all 15 on equity — crypto 0/54 decisively.
- By vol regime: low 14/36, mid 1/36, high 0/36 — edge concentrated in low-vol equity.
- Best cell: QQQ, slope_window=10, hold_days=9, low-vol tercile, Sharpe 2.75.
- Worst cell: SPY, slope_window=20, hold_days=5, low-vol tercile, Sharpe -0.87.

## Single-config validators (slope_window=10, hold_days=9, full sample 2017-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.996 (FAIL, thr 1.0 — 0.35% shortfall, razor-thin near-miss) | 0.167 (pass) | 0.871 (pass) | 1.00 pass_fraction (pass; 4/4 splits) | rel_std 0.444 (pass, thr 0.5) |
| SPY | 0.649 (FAIL) | 0.128 (pass) | 0.499 (FAIL, thr 0.5, essentially tied) | 0.75 pass_fraction (pass; 3/4 splits) | rel_std 0.953 (FAIL, thr 0.5) |

Walk-forward used a manual 4-split RangeSplitter (vectorbt.utils.splitting
unavailable in the installed vectorbt version, same known repo-wide
workaround as many prior entries).

## Decision: REJECT (QQQ is a genuine near-miss worth revisiting)

QQQ fails ONLY on Sharpe, and by a razor-thin margin (0.996 vs 1.0 threshold,
a 0.35% shortfall) — every other validator (MDD, TC-survival, walk-forward
4/4, parameter sensitivity) passes cleanly. This is one of the closest
near-misses seen in this repo's history and is a strong candidate for a
future loop's direct parameter-tweak follow-up (e.g. widening the grid
slightly around slope_window=10/hold_days=9, or trying an alternate exit
that isn't purely time-based). SPY decisively fails 3 of 5 validators
(Sharpe, TC-survival essentially tied at threshold, and high parameter
sensitivity — rel_std 0.95 indicates the SPY result is fragile/config-
dependent, unlike QQQ's more stable 0.44). Crypto rejected decisively across
the whole grid (0/54 cells).
