# XLU/SPY Beta Rotation Regime Filter — Backtest Report

**Date:** 2026-09-05
**Strategy file:** `strategies/2026-09-05_xlu_spy_beta_rotation_regime.py`
**KB id:** 2026-09-05-067

## Hypothesis

Per Michael Gayed's Lead-Lag Report (leadlagreport.com, multiple weekly
issues, e.g. "The framework's core risk check (XLU/SPY 4-week ROC)
flipped from Risk-On to Risk-Off at +8.34%"): the "Beta Rotation" signal
uses the sign of the trailing-4-week rate of change of the XLU/SPY ratio.
Utilities (XLU, low-beta defensive sector) outperforming the broad market
(positive ROC) signals defensive rotation (risk-off); underperforming
(negative ROC) signals risk appetite / beta chasing (risk-on). First
XLU/SPY-based strategy in this repo, distinct from all other cross-asset
ratio regime filters tested (gold/silver, copper/gold, XLY/XLP, IWM/SPY,
RSP/SPY, SPY/TLT).

## Step 6 — Grid test (roc_window x QQQ/SPY/BTC/ETH x 3 vol regimes)

- param_grid: `roc_window=[15,20,25]` (~4 trading weeks = 20d default)
- symbols: equity `[QQQ, SPY]`, crypto `[BTC/USDT, ETH/USDT]`
- vol_regime_splits=3
- 36 total cells, 8 passed (pass_fraction = 0.222)
- by_asset_class: equity 8/18; crypto 0/18 (decisive fail -- XLU/BTC ratio is not a meaningful risk signal for crypto)
- by_vol_regime: low 6/12; mid 0/12; high 2/12
- best full-regime-coverage config: SPY roc_window=25 (2/3 regimes pass: low 2.92, mid fails 0.45, high 1.29)

## Step 7 — Single-config validators (roc_window=25)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full period) | **1.19 — PASS** | **1.36 — PASS** | >= 1.0 |
| Max drawdown | **0.172 — PASS** | **0.129 — PASS** | <= 0.25 |
| Transaction cost survival (10bps/trade, ~93/77 trades) | **1.06 — PASS** | **1.22 — PASS** | net Sharpe >= 0.5 |
| Walk-forward (4-split, manual fallback) | **1.00 — PASS** | **1.00 — PASS** | >= 0.75 |
| Parameter sensitivity (3-value roc_window sweep) | **0.183 — PASS** | **0.155 — PASS** | <= 0.5 |

Unlike the grid's regime-fragmented mid-vol weakness, the full-period
unconditional Sharpe on both QQQ (1.19) and SPY (1.36) clears the
threshold cleanly, with very low drawdown (13-17%), low trade frequency
(77-93 round trips over ~7.5 years -- an infrequent regime-switch signal,
not a high-turnover oscillator), and a perfect 4/4 walk-forward pass on
both symbols. Parameter sensitivity is also low (relative std ~0.15-0.18
across the 3-value sweep).

## Step 8 — Decision: **ACCEPT (equity: QQQ, SPY)**

All validators pass cleanly on both QQQ and SPY using `roc_window=25`.
Crypto is a decisive 0/18 grid fail (the XLU/underlying ratio applied to
BTC/ETH close prices is not a meaningfully interpretable signal --
scope this strategy strictly to equity). Strategy file and this report
are kept live in `strategies/`/`backtests/`.
