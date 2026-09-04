# Backtest Report: Squeeze Momentum Indicator (LazyBear) + EMA Filter (2026-09-04)

**Strategy file:** `strategies/2026-09-04_squeeze_momentum_ema_filter.py`
**Knowledge base id:** 2026-09-04-126
**Outcome:** REJECTED

## Hypothesis

LazyBear's Squeeze Momentum Indicator: BB(20,2std) inside KC(20-EMA +/-
kc_mult*ATR(20)) detects a volatility squeeze; a linear-regression momentum
histogram gauges direction. Per enlightenedstocktrading.com's own systematic
rule: enter long on the first squeeze-release bar if momentum is positive
and rising and price is above the 50-day EMA. Distinct from the prior
rejected plain TTM Squeeze (2026-09-04-091) by adding the EMA trend filter
and restricting to first-release-bar-only entries.

Source: https://enlightenedstocktrading.com/squeeze-momentum-indicator/

## Grid test summary (kc_mult in {1.5,2.0} x trend_window in {50,100}, max_hold_days=15, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 48, passed_cells: 2, pass_fraction: 0.0417
- by_asset_class: equity 2/24, crypto 0/24
- by_vol_regime: low 2/16, mid 0/16, high 0/16
- best_cell: SPY, kc_mult=2.0, trend_window=100, low-vol, Sharpe=2.091

## Single-config validation (kc_mult=2.0, trend_window=100, max_hold_days=15)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.299 (FAIL) | 0.801 (FAIL, near-miss) | >= 1.0 |
| Max drawdown | 0.127 (PASS) | 0.097 (PASS) | <= 0.25 |
| TC survival (net Sharpe) | 0.240 (FAIL) | 0.708 (PASS) | >= 0.5 |

Walk-forward/parameter-sensitivity skipped given the low overall
pass_fraction and QQQ's decisive Sharpe/TC failure.

## Verdict

Rejected. Squeeze-release signals are rare (25-29 trades over 7.7yr),
producing fragile, low-pass-fraction results consistent with the
already-rejected plain TTM Squeeze variant. Crypto rejected outright
(0/24 grid cells). Second consecutive squeeze-family rejection on
low-trade-count fragility.
