# Backtest Report: Larry Williams-Style Volatility Breakout (Daily-Bar Adaptation)

**Strategy file:** `strategies/2026-09-04_lw_volatility_breakout.py`
**Knowledge base id:** 2026-09-04-069

## Hypothesis

Per DisciplineAI's Larry Williams Volatility Breakout article: Range =
PriorHigh - PriorLow; long entry trigger = PriorHigh + k*Range (k=0.25-0.4
typical for daily swing). Original system is an intraday stop-buy order;
adapted here to daily bars: long entry when today's close exceeds the
trigger; exit after `max_hold_days` or when close falls below the
prior-day low. Distinct from Donchian breakout (-008/-054, N-day rolling
extreme) since this uses only the single PRIOR day's range scaled by k.

Source: https://www.disciplineaiapp.com/post/volatility-breakout-strategy
(web_search succeeded first try).

## Grid test summary

- Grid: `k` in {0.25,0.4} x `max_hold_days` in {3,5} x symbols
  {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol-regime terciles = 48 cells.
- pass_fraction: 0.167 (8/48)
- by_asset_class: equity 8/24, crypto 0/24
- by_vol_regime: low 7/16, mid 1/16, high 0/16
- best_cell: SPY, k=0.25/hold=3, low-vol tercile, Sharpe 2.32
- worst_cell: QQQ, k=0.25/hold=3, high-vol tercile, Sharpe -1.05

## Full-sample sweep (4 k/hold combos)

| Symbol | k=0.25,h=3 | k=0.4,h=3 | k=0.25,h=5 | k=0.4,h=5 |
|---|---|---|---|---|
| QQQ | -0.106 | 0.277 | 0.146 | 0.418 |
| SPY | 0.465 | **0.651** | 0.263 | 0.391 |

Primary config selected: `k=0.25, max_hold_days=3` (source's default k).

## Single-config validator suite (primary config, k=0.25/hold=3)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | -0.106 (fail, thr 1.0) | 0.465 (fail, thr 1.0) |
| Max drawdown | 0.364 (fail, thr 0.25) | 0.252 (fail, thr 0.25, borderline) |
| TC survival | -0.347 (fail, thr 0.5) | 0.025 (fail, thr 0.5) |
| Walk-forward | 2/4 splits positive (fail) | 3/4 splits positive (pass) |
| Parameter sensitivity | rel.std 1.051 (fail) | rel.std 0.317 (pass) |

## Outcome

**Rejected.** Extremely high trade frequency (289 and 276 completed
round-trips over 7.7yr, roughly one every 7 trading days) drives severe
transaction-cost drag and destabilizes the signal. QQQ fails 4 of 5
validators decisively; SPY fails Sharpe, MDD, and TC-survival. Best combo
(SPY, k=0.4/hold=3, Sharpe 0.651) is still a decisive miss. Crypto
rejected decisively (0/24 grid cells).

## Notes

Novelty: first single-prior-day-range breakout strategy (as opposed to
Donchian's rolling N-day extreme) in this repo. The daily-bar adaptation
of an inherently intraday stop-order system is a likely structural
mismatch — the prior single day's range is a noisy, high-variance
threshold on daily bars (unlike a smoothed N-day channel), producing
near-continuous whipsaw entries. A future loop attempting this family
should likely require intraday data (not available in this repo's
loaders) rather than a daily-bar close-based proxy.
