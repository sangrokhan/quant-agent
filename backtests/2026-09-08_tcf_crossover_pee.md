# Backtest Report: Trend Continuation Factor (TCF) Crossover (2026-09-08_tcf_crossover_pee.py)

**Hypothesis / source:** M.H. Pee's Trend Continuation Factor (TASC Vol.
20:3, March 2001), exact formula transcribed from
https://www.prorealcode.com/prorealtime-indicators/trend-continuation-factor/
(ProRealTime PRT source, verified against conceptual descriptions on
https://www.linnsoft.com/techind/trend-continuation-factor and
https://www.tradingpedia.com/forex-trading-indicators/trend-continuation-factor):
TCF+ and TCF- are dual cumulative-summation lines built from the signed
1-bar ROC, each accumulating its own-sign component while resetting to
zero on every sign flip of the OTHER component. Long entry when TCF+
crosses above TCF- (the source's own disclosed alternative to the simple
positive/negative threshold rule); exit on the mirror bearish cross or a
max_hold_days time-stop.

## Grid test summary (sumperiod=[20,35,50] x max_hold_days=[10,15,20],
## QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026-09)

- Total cells: 108, passed: 19, pass_fraction = 0.176
- By asset class: equity 19/54, crypto 0/54 (decisive fail)
- By vol regime: low 7/36, mid 5/36, high 7/36 -- unusually well-spread
  across regimes (most rejected strategies in this repo concentrate in
  one regime only)
- Best cell: QQQ, sumperiod=50/max_hold_days=15, low-vol, Sharpe 2.384
- Worst cell: SPY, sumperiod=50/max_hold_days=10, low-vol, Sharpe -1.028

## Single-config validators (best config: sumperiod=50, max_hold_days=15),
## full sample 2019-2026-09

| Metric | SPY | QQQ | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe | 0.577 | 1.357 | >= 1.0 | FAIL SPY / PASS QQQ |
| Max Drawdown | 21.1% | 9.7% | <= 25% | PASS (both) |
| TC-survival net Sharpe (10bps, 29 trades) | 0.491 | 1.276 | >= 0.5 | FAIL SPY (razor-thin) / PASS QQQ |
| Walk-forward (manual 4-split) | 3/4 (75%) | 4/4 (100%) | >= 75% | PASS (both) |
| Parameter sensitivity (QQQ, 9-cell sumperiod x max_hold_days sweep) | -- | relative_std 0.433 | <= 0.5 | PASS |

## Verdict: ACCEPTED (QQQ only); REJECTED (SPY, near-miss on Sharpe + razor-thin TC-survival miss)

QQQ passes all five validators cleanly: Sharpe 1.357, MDD 9.7% (very low),
TC-survival 1.276 (comfortably above 0.5 even with 29 round-trip trades),
walk-forward 4/4, and parameter sensitivity 0.433 (well within the 0.5
robustness threshold across a 3x3 sumperiod/max_hold_days sweep). SPY
misses Sharpe (0.577) and just misses TC-survival (0.491 vs 0.5) -- kept
scoped to QQQ only per repo convention for asymmetric accepts. Crypto
rejected decisively (0/54).
