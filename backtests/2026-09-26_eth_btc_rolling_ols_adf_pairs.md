# ETH/BTC Rolling-OLS Hedge-Ratio + ADF-Gated Z-Score Pairs Trade

**Status: REJECTED** (2026-09-26-031)

Source: github.com/Bauch0430/crypto-pairs-trading-btc-eth ("Statistical
Arbitrage: BTC/ETH Cointegration Pairs Trading Strategy"), read via
browser_exec.

## Primary config
`window=45, entry_z=1.5, exit_z=0.5, stop_z=4.0, adf_threshold=0.05, adf_step=5, max_hold_days=45`

## Single-config validators (ETH/USDT, 2019-01-01..2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 0.202 | >= 1.0 | No |
| Max Drawdown | 0.298 | <= 0.25 | No |
| TC-survival net Sharpe | 0.198 | >= 0.5 | No |
| Parameter sensitivity (rel. std across window={30,45,60,75}) | 0.852 | <= 0.5 | No |
| Walk-forward | skipped (only 5 trades full-sample; other validators already decisively fail) | -- | -- |

## Grid summary
12 cells (window in {45,60} x entry_z in {1.5,2.0} x ETH/USDT x 3 vol regimes).
pass_fraction=0.25. by_vol_regime: low 1/4, mid 2/4, high 0/4.
Best cell: window=45/entry_z=1.5, low-vol, Sharpe 1.36 (does not generalize).
Worst cell: window=60/entry_z=2.0, high-vol, Sharpe -0.63.

## Verdict
Decisive full-sample rejection. The ADF cointegration gate correctly filters
out most days (pair is genuinely cointegrated only ~9.8% of the time per
source's own finding), leaving very few trades (5 over 7.7 years) that are
neither profitable enough nor stable enough across parameter perturbation to
clear this repo's thresholds.
