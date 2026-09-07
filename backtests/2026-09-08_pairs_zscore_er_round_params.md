# Pairs Trading: JPM/BAC Z-Score + ER Regime Gate (round/fixed parameters)

**Strategy file:** reuses `strategies/2026-09-08_pairs_zscore_er_regime_gate.py` (same code as 2026-09-08-072, different fixed config — no new strategy file)
**Sources:** same as 2026-09-08-071/072 (quantifiedstrategies.com pairs-trading article; tradewink.com ER regime-gate guide)

## Hypothesis

Follow-up to near-miss `2026-09-08-072` (ER-gated pairs z-score, Sharpe 1.059
pass but parameter_sensitivity 0.505 narrowly fail). Test whether fixing
round, non-grid-argmax parameter values (`er_period=20, er_threshold=0.4`
instead of the grid's literal best cell `er_period=30, er_threshold=0.45`)
flattens the parameter surface enough to pass sensitivity, per
`2026-09-08-072`'s own notes.

## Result: parameter sensitivity now passes, but Sharpe now fails

Config: `hedge_window=90, z_window=15, entry_z=1.5, exit_z=0.3,
max_hold_days=15, er_period=20, er_threshold=0.4`.

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.972 | 1.0 |
| Max drawdown | ✅ (narrow) | 0.238 | 0.25 |
| Transaction cost survival | ✅ | 0.935 net Sharpe | 0.5 |
| Walk-forward (manual 4-slice) | ✅ | 3/4 splits positive | 0.75 |
| Parameter sensitivity (finer 3x3 grid around fixed values, er_period {15,20,25} x er_threshold {0.35,0.4,0.45}) | ✅ | relative_std **0.200** | 0.5 |

Grid summary (same finer param grid, vol_regime_splits=3): equity JPM/BAC
pass_fraction 12/27 (0.444), by_vol_regime low=8/9, mid=3/9, high=1/9.
Crypto ETH/BTC pass_fraction 0/27, still decisively rejected.

## Decision: **REJECTED** (confirms the Sharpe/robustness tradeoff is fundamental, not a tuning artifact)

This directly confirms `2026-09-08-072`'s hypothesis: the grid-argmax
config (`er_period=30, er_threshold=0.45`) buys its Sharpe-over-1.0 pass at
the cost of param instability, while round/fixed values that flatten the
parameter surface (relative_std drops from 0.505 to 0.200 — a large,
genuine improvement) pull full-sample Sharpe back below 1.0 (0.972) and
push MDD uncomfortably close to its own budget (0.238 vs 0.25). This is
not an implementation bug or an arbitrary choice — three parameter-value
attempts across two iterations (2026-09-08-071 ungated: Sharpe 0.954;
-072 argmax-gated: Sharpe 1.059/param-fail; -073 round-gated: Sharpe
0.972/param-pass) all land in the same 0.95-1.06 Sharpe band, suggesting
this pair's true edge sits right around the 1.0 threshold regardless of
exact regime-gate tuning — a genuine near-miss ceiling for the JPM/BAC
pairs-trading idea as implemented, not a parameter-search artifact.

**Notes for future iterations:** don't keep re-tuning JPM/BAC er_threshold/
er_period further — three attempts have converged on the same ~1.0 Sharpe
ceiling. A more promising path per `2026-09-08-071`'s original notes would
be testing a *different* equity pair (e.g. XOM/CVX, KO/PEP) where the
correlation structure differs from money-center banks, rather than
continuing to tune this specific pair's regime gate.
