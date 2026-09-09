# 2026-09-10 — HYG/IEF Credit-Risk Rotation (REJECTED)

## Hypothesis

Per an iM-Best "Bond Market Trader" blog post (indexswingtrader.blogspot.com,
2019): "generally, when equity returns are good, high yield bonds
outperform investment grade/Treasury bonds" — so a relative-momentum
rotation between HYG (high-yield credit) and IEF (7-10yr Treasuries),
hold whichever has the higher trailing lookback_days return with an
absolute-momentum gate, should capture credit-cycle risk-on/risk-off shifts.
The original model's 6 proprietary stock-market timers + CAPE threshold are
not reproducible; this tests the simplified, fully disclosed GEM (Gary
Antonacci Dual Momentum) mechanic applied bond-vs-bond instead of
equity-vs-bond.

Strategy file: `strategies/2026-09-10_hyg_ief_credit_rotation.py`
(reuses the exact GEM simulation code from
`2026-09-07_gem_dual_momentum_spy_ief.py`, retargeted to HYG-vs-IEF).

## Parameter sweep (lookback_days, monthly rebalance)

| lookback_days | Sharpe | MDD |
|---|---|---|
| 60 | -0.131 | 0.226 |
| 90 | -0.231 | 0.228 |
| 126 | -0.077 | 0.227 |
| 180 | 0.036 | 0.226 |
| 252 | -0.240 | 0.262 |

Every tested lookback produces a negative or near-zero Sharpe ratio — no
config comes remotely close to the 1.0 threshold.

## Decision: REJECT

The relative-momentum mechanism that works for equity-vs-bond GEM rotations
(SPY-vs-IEF accepted at Sharpe 1.046 in 2026-09-07-023) does not transfer to
a bond-vs-bond (credit-vs-duration) pairing: HYG and IEF returns are close
enough in magnitude and volatility that the monthly relative-momentum signal
is mostly noise, with no economically meaningful edge captured. Not
implemented as a grid test — the single-parameter sweep already shows no
config anywhere close to passing, so a full multi-asset-class/vol-regime
grid would not change the conclusion (and HYG/IEF is a fixed pair with no
crypto analogue in any case).
