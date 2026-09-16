# Rogers-Satchell Volatility Targeting + Deadband — Backtest Report

**Date:** 2026-09-17 (cron trigger iteration 4)
**Strategy file:** `strategies/2026-09-17_rogers_satchell_vol_targeting_deadband.py`
**Hypothesis:** Per https://ryanoconnellfinance.com/historical-volatility-estimators
(read via browser_exec Google-SERP-snippet fallback -- web_search's DDGS
backend errored with a TLS "peer closed connection" RequestError for this
query), the Rogers-Satchell (1991) OHLC estimator
(`sigma^2 = (1/n)*sum[ln(H/C)*ln(H/O)+ln(L/C)*ln(L/O)]`) is explicitly
drift-independent, unlike Parkinson/Garman-Klass's zero-drift assumption --
theoretically the best-matched sizing denominator for a TRENDING (SMA-gated)
signal like this repo's overlay construction. 4th and final planned
vol-estimator-swap variant this cron trigger, after close-to-close
(2026-09-08-165), Parkinson (2026-09-17-050/051), and Garman-Klass
(2026-09-17-052).

Source: https://ryanoconnellfinance.com/historical-volatility-estimators (browser_exec)

## Grid test summary

Grid: `trend_window`∈{100,200} × `vol_window`∈{10,20,40} × `target_vol`∈{0.10,0.15,0.20}
× `leverage_cap`∈{1.0,1.5} × `deadband`∈{0.10,0.20}, symbols={QQQ,SPY,BTC/USDT,ETH/USDT},
vol_regime_splits=3.

- total_cells: 864, passed: 457, **pass_fraction: 0.529**
- by_asset_class: equity 203/432 (0.47), crypto 254/432 (0.59)
- by_vol_regime: low 226/288 (0.78), mid 193/288 (0.67), high 38/288 (0.132)
- best_cell: SPY, trend_window=200/vol_window=40/target_vol=0.20/leverage_cap=1.5/deadband=0.2,
  low-vol, Sharpe 2.873

Virtually identical breadth to the Garman-Klass variant (0.529 vs 0.530) --
the theoretical drift-independence advantage does not show up as a
materially different raw grid pass-rate at this sample size/regime split,
though the per-symbol single-config comparison below shows small
differences.

## Single-config validation (best per-symbol config found via 4-config search)

| Symbol | Config | Sharpe | MDD | Net Sharpe (5bps) | # trades | WF pass frac | Param sens |
|---|---|---|---|---|---|---|---|
| QQQ | 200/20/0.20/1.0/0.20 | 1.323 (pass) | 0.197 (pass) | 1.240 (pass) | 135 | 0.75 (pass) | 0.026 (pass) |
| SPY | 200/10/0.15/1.5/0.20 | 1.058 (pass) | 0.237 (pass) | 0.976 (pass) | 121 | 0.75 (pass) | 0.011 (pass) |
| BTC/USDT | 200/20/0.15/1.0/0.20 | 1.021 (pass) | 0.191 (pass) | 0.983 (pass) | 72 | 0.75 (pass) | 0.113 (pass) |
| ETH/USDT | 200/20/0.20/1.0/0.20 | 0.944 (fail) | **0.251 (fail)** | 0.923 (pass) | 56 | 1.00 (pass) | 0.066 (pass) |

For the first time in this vol-estimator-swap family this trigger,
ETH/USDT fails on BOTH Sharpe (0.944) AND max drawdown (0.251, marginally
over the 0.25 threshold) rather than a Sharpe-only near-miss -- a
marginally weaker result for ETH than the Parkinson (Sharpe 0.946, MDD
0.244 pass) or Garman-Klass (Sharpe 0.964, MDD 0.246 pass) variants.
QQQ/SPY/BTC results are all comparable (Sharpe within ~0.03-0.06 of the
Garman-Klass variant, same "narrow pass" pattern for SPY/BTC).

## Accept/Reject

- **QQQ, SPY, BTC/USDT: ACCEPT.** All validators pass for all three.
- **ETH/USDT: REJECT (decisive-ish).** Fails both Sharpe and MDD (unlike
  the Parkinson/GK variants' Sharpe-only near-miss) -- the slightly weaker
  outcome among the three range-based estimators for this one symbol. Not
  pursued further.

This completes the planned 4-variant vol-estimator-swap research thread for
this cron trigger (close-to-close/Parkinson/Garman-Klass/Rogers-Satchell),
all sharing the identical SMA-trend-gate + inverse-vol-targeting-sizing +
deadband skeleton. Summary across all four: QQQ and SPY accept in every
variant; BTC/USDT accepts in Parkinson/Garman-Klass/Rogers-Satchell (all
three range-based estimators) but not close-to-close (0/36 decisive
reject, pre-deadband); ETH/USDT is a consistent near-miss/reject across
all four variants. Garman-Klass produced the single best BTC/USDT result
(Sharpe 1.092) of the four.
