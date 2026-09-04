# Backtest Report: HYG/LQD Credit Spread Regime Filter

**Strategy file:** `strategies/2026-09-05_hyg_lqd_credit_regime.py`
**Hypothesis id:** 2026-09-05-025
**Source:** https://www.thetrading.tools/credit-spreads

## Hypothesis

The HYG/LQD ratio (high-yield vs investment-grade corporate bond ETFs) is a daily-tradeable
proxy for credit risk appetite; a rolling 1-year z-score of the ratio dropping below a
threshold (widening credit spreads, risk-off) historically precedes equity market stress.
Long equities while z >= risk_off_z; flat when z < risk_off_z. Tested on QQQ/SPY and
BTC/USDT, ETH/USDT (falsification check).

## Grid test summary (validation/grid_test.py::run_strategy_grid)

- Grid: `zscore_window` in {126, 252} x `risk_off_z` in {-0.5, -1.0, -1.5} x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles, 2019-01-01 to 2026-09-01.
- 72 total cells, **15 passed (pass_fraction = 20.8%)**.
- By asset class: equity 15/36 (42%), crypto 0/36 (falsification succeeded).
- By vol regime: low 12/24 (50%), mid 1/24, high 2/24.
- Best cell: `zscore_window=252, risk_off_z=-1.5`, SPY, low-vol, Sharpe 2.64 (narrow slice).

## Single-config validation (zscore_window=252, risk_off_z=-1.5, full sample 2019-2026)

| Symbol | Sharpe | MDD | Net Sharpe after 10bps costs (51 trades) | Param sensitivity (rel. std across 6 configs) |
|---|---|---|---|---|
| QQQ | 0.96 (fail, thr 1.0) | 35.6% (fail, thr 25%) | 0.92 (pass, thr 0.5) | 0.24 (pass, thr 0.5) |
| SPY | 0.97 (fail, thr 1.0) | 25.4% (fail, thr 25%) | 0.91 (pass, thr 0.5) | 0.18 (pass, thr 0.5) |

Both symbols land just under the Sharpe threshold (0.96-0.97 vs 1.0) at the loosest
`risk_off_z=-1.5` config (which minimizes false-positive flat periods); tighter thresholds
(-0.5, -1.0) perform worse. MDD fails on both -- identical to the yield-curve strategy's
issue (2026-09-05-024): the underlying drawdown is dominated by the 2022 broad equity bear
market, which the credit-spread signal doesn't flag as risk-off early/strongly enough to
avoid.

## Verdict: REJECTED

Sharpe fails on both symbols (0.96, 0.97 vs 1.0 threshold) at the best full-sample config;
MDD also fails on both (35.6%, 25.4% vs 25% threshold). Transaction-cost survival and
parameter sensitivity both pass. This is a moderate near-miss (closer than most of this
repo's rejected strategies but weaker than the yield-curve un-inversion strategy
2026-09-05-024, which passed Sharpe/TC/param-sensitivity decisively and only missed on MDD).
Crypto falsification succeeded (0/36 cells). A future loop could combine this credit-spread
filter with the yield-curve un-inversion signal (2026-09-05-024) as a multi-factor risk-off
composite, since both flag similar macro deterioration but neither alone clears all
validators.
