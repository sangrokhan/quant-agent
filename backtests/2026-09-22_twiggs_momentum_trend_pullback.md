# Twiggs Momentum Trend-Pullback (Backtest Report — REJECTED)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_twiggs_momentum_trend_pullback.py`
**KB id:** 2026-09-22-007

## Hypothesis

Per MarketCalls' disclosed trading rules
(https://www.marketcalls.in/sensex/twiggs-momentum-oscillator-for-sensex.html)
for Colin Twiggs' Momentum Oscillator: identify trend via price vs
EMA(63); in an uptrend, go long when the oscillator (EMA-smoothed ROC,
exact proprietary formula not publicly disclosed -- implemented here per
IncredibleCharts' own "smoothed ROC" description) turns upward after
dipping toward/below zero. First test of Twiggs Momentum in this repo.

## Grid test summary (Step 6)

`param_grid={roc_window:[14,21], max_hold_days:[15,20,30]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3` → 72 cells total.

- Overall pass_fraction: 0.347 (25/72)
- By asset class: equity 18/36, crypto 7/36
- By vol regime: low 14/24, mid 10/24, high 1/24 (high-vol regime almost
  uniformly fails on both asset classes, several strongly negative Sharpes)
- Best cell: ETH/USDT roc_window=21/max_hold_days=30, mid-vol, Sharpe=2.51
- Best equity config candidates: QQQ (roc_window=21, max_hold_days=20) and
  (roc_window=14, max_hold_days=30) both passed low+mid vol regime cells
  (2/3).

## Single-config validation (Step 7) — two QQQ/SPY candidate configs tested

**Config A: roc_window=21, max_hold_days=20**

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe | 0.771 ❌ | 0.111 ❌ |
| MDD | 0.139 ✅ | 0.183 ✅ |
| TC survival | 0.698 ✅ | 0.017 ❌ |
| Walk-forward | 1.0 ✅ | 0.75 ✅ |
| Param sensitivity | 0.141 ✅ | 0.600 ❌ |

**Config B: roc_window=14, max_hold_days=30**

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe | 0.838 ❌ | 0.975 ❌ |
| MDD | 0.189 ✅ | 0.179 ✅ |
| TC survival | 0.754 ✅ | 0.850 ✅ |
| Walk-forward | 0.75 ✅ | 1.0 ✅ |
| Param sensitivity | 0.141 ✅ | 0.600 ❌ |

Neither config clears the Sharpe threshold (1.0) on either symbol in
full-sample testing, despite promising grid cells in isolated low/mid-vol
terciles -- the grid's apparent edge does not survive full-sample
validation. This is consistent with the grid's own vol-regime breakdown
showing the edge is regime-concentrated rather than a genuine full-sample
effect.

## Decision

**Reject.** Full-sample Sharpe fails on both QQQ and SPY across both
tested parameter configs (best QQQ Sharpe 0.838, best SPY Sharpe 0.975,
both below the 1.0 threshold). Crypto not pursued further given the
mixed/inconsistent equity results. The exact proprietary Twiggs Momentum
formula (Colin Twiggs' specific weighted-ROC construction) was not
publicly disclosed by any source found this iteration -- this repo's
plain EMA-smoothed-ROC approximation may not faithfully replicate the
original indicator, a caveat for any future revisit.
