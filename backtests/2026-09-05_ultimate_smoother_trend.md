# Ehlers Ultimate Smoother Trend-Following — Backtest Report

**Date:** 2026-09-05
**Strategy file:** `strategies/2026-09-05_ultimate_smoother_trend.py`
**KB id:** 2026-09-05-066

## Hypothesis

Per https://financial-hacker.com/ehlers-ultimate-smoother/ (converting John
Ehlers' TASC 3/24 EasyLanguage): the Ultimate Smoother is a near-zero-lag
2nd-order recursive highpass-subtraction price filter, "the best, albeit
smoothed, representation of the price curve" vs plain EMA/SuperSmoother.
A reader comment on the source article suggested testing "being long when
price is higher than the smoother" as the natural trend rule. This
strategy adds a slope confirmation (smoother itself rising) to reduce
whipsaws. First Ultimate-Smoother-based strategy in this repo.

## Step 6 — Grid test (smoother_length x slope_lookback x max_hold_days x QQQ/SPY/BTC/ETH x 3 vol regimes)

- param_grid: `smoother_length=[15,20,30]`, `slope_lookback=[3,5]`, `max_hold_days=[20,30]`
- symbols: equity `[QQQ, SPY]`, crypto `[BTC/USDT, ETH/USDT]`
- vol_regime_splits=3
- **144 total cells, 42 passed (pass_fraction = 0.292)**
- by_asset_class: equity 42/72; **crypto 0/72 (decisive fail)**
- by_vol_regime: low 22/48; mid 16/48; high 4/48 (weak but non-zero)
- best_cell: QQQ, smoother_length=15/slope_lookback=5/max_hold_days=20, mid-vol, Sharpe=2.38
- Best full-regime config candidate: QQQ smoother_length=15/slope_lookback=5/max_hold_days=20 (2/3 regimes pass: low 1.48, mid 2.38, high fails -0.73)

## Step 7 — Single-config validators (smoother_length=15, slope_lookback=5, max_hold_days=20)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full period) | 0.47 — FAIL | 0.13 — FAIL | >= 1.0 |
| Max drawdown | 0.302 — FAIL | 0.213 — PASS | <= 0.25 |
| Transaction cost survival (10bps/trade, ~225/233 trades) | 0.08 — FAIL | -0.26 — FAIL | net Sharpe >= 0.5 |
| Walk-forward (4-split, manual fallback) | 0.75 — PASS | 0.75 — PASS | >= 0.75 |
| Parameter sensitivity | 0.184 — PASS | 0.530 — FAIL | <= 0.5 |

As with several other regime-fragmented Ehlers-family strategies tested
in this repo, the promising per-regime grid Sharpe (up to 2.38 in mid-vol
QQQ) does not survive unconditional full-period testing: both symbols
fail full-period Sharpe decisively, and transaction costs (~225-233 round
trips) turn net Sharpe negative or near-zero on both.

## Step 8 — Decision: **REJECT**

Decisive rejection: full-period Sharpe and transaction-cost survival fail
on both QQQ and SPY. Crypto is a decisive 0/72 grid fail. Strategy/report
kept as a record of a rejected attempt — this is NOT a live strategy.
