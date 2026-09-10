# 2026-09-10 — Zero Lag MACD Crossover + SMA Trend Filter (ACCEPTED, SPY only)

## Hypothesis

Per https://www.quantifiedstrategies.com/zero-lag-macd/ (John Ehlers & Rick
Way's Zero Lag MACD): apply the classic MACD-line/signal-line crossover
mechanic to *de-lagged* ("zero-lag") EMAs instead of plain EMAs, using the
source's disclosed double-EMA de-lag trick (EMA of an EMA, extrapolated by
the difference) at both the fast/slow EMA stage and again at the signal-line
stage. Zero Lag MACD crossing above its zero-lag signal line signals a long
entry; crossing back below exits. The source's own caveat is that removing
lag increases whipsaw sensitivity in sideways markets, so an SMA(trend_window)
trend filter gates entries/holds to bullish regimes only. First Zero Lag MACD
strategy tested in this repo (distinct from this repo's many classic-MACD
histogram/divergence variants, which use plain, not de-lagged, EMAs).

Strategy file: `strategies/2026-09-10_zero_lag_macd_crossover.py`

## Grid summary (trend_window in [50,100,150] x signal_period in [9,14], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- 14/72 cells passed (pass_fraction 0.194), ALL 14 passes on equity — crypto 0/36 decisively.
- By vol regime: low 12/24, mid 2/24, high 0/24 — edge concentrated in low-vol equity.
- Best cell: SPY, trend_window=100, signal_period=14, low-vol tercile, Sharpe 2.55.
- Worst cell: QQQ, trend_window=50, signal_period=9, high-vol tercile, Sharpe -0.84.

## Single-config validators (trend_window=100, signal_period=14, full sample 2017-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| SPY | 1.062 (pass, thr 1.0) | 0.125 (pass, thr 0.25) | 0.767 (pass, thr 0.5) | 0.75 pass_fraction (pass, thr 0.75; manual 4-split RangeSplitter workaround since `vectorbt.utils.splitting` is unavailable in the installed vectorbt version) | rel_std 0.154 (pass, thr 0.5) |
| QQQ | 0.314 (FAIL) | 0.239 (pass) | 0.158 (FAIL) | not evaluated (already decisive fail) | rel_std 0.310 (pass) |

Walk-forward per-split Sharpes for SPY: 2017-01→2019-06: 1.56; 2019-06→2021-10:
1.77; 2021-10→2024-04: 0.15; 2024-04→2026-09: -0.09 (3/4 splits positive =
0.75 pass_fraction, right at threshold — the two most recent 2.3yr windows
are markedly weaker than 2017-2021, worth flagging as a fragility to monitor,
not just a clean pass).

## Decision: ACCEPT (SPY-only scope)

All 5 validators pass for SPY at the grid's best config. QQQ decisively fails
Sharpe and transaction-cost survival at the same config (94 vs 106 trades,
QQQ's higher trade frequency and lower directional edge in this indicator
combination). Crypto rejected decisively across the whole grid (0/36).
Narrow, honest scope: SPY only, low/mid-vol equity regimes primarily (12/14
of the equity passes are in the low-vol tercile) — record this explicitly so
a future loop doesn't over-trust it broadly. The declining walk-forward
Sharpe in the most recent two sub-periods (0.15, then negative) is a
near-term robustness flag worth revisiting if this strategy is ever
paper-traded.
