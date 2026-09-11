# Backtest Report: 3-Factor Regime Allocation (Trend, Volatility, Credit) -- TASC 2026.07

**Strategy file:** `strategies/2026-09-12_regime_trend_vol_credit_tiered.py`
**Status:** REJECTED (strongest near-miss this cron trigger)

## Hypothesis
Per TASC July 2026 Traders' Tips, "Market Regime Identification Using
Trend, Volatility, And Credit Conditions" (Gaetano Di Prima & Fabio Baruffa),
via https://www.tradingview.com/script/wu1VhNpf-TASC-2026-07-Risk-On-Risk-Off-Or-Caution/
(exact rules fully disclosed):

Weekly regime = count of 3 favorable boolean conditions (trend: close>200d
SMA; volatility: VIX<VIX3M; credit: 100d z-score of HYG/IEF ratio > 0).
Exposure set at next Monday's open: 3/3 favorable -> 100% exposure, 2/3 ->
50%, 0-1/3 -> 0%. First fractional-position-weight 3-factor tiered-exposure
strategy tested in this repo (each single-factor ingredient already tested
standalone and rejected/near-miss: VIX/VIX3M term structure 2026-09-04-157,
HYG/LQD credit spread 2026-09-05-025).

## Grid test summary (Step 6)
- Grid: trend_window ∈ {150,200}, credit_zscore_window ∈ {80,100}; symbols
  QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3.
- Total cells: 48, passed: 16, **pass_fraction = 0.333** (best this cron
  trigger)
- By asset class: equity 16/24, crypto 0/24 (decisive reject -- expected,
  strategy uses US-market-specific VIX/HYG/IEF signals)
- By vol regime: low 8/16, mid 8/16, high 0/16 (both low AND mid vol
  terciles pass -- broader regime coverage than prior near-misses this
  trigger, which were low-vol-only)
- Best cell: trend_window=150, credit_zscore_window=80, SPY, low-vol
  tercile, Sharpe=2.21
- Worst cell: trend_window=150, credit_zscore_window=80, SPY, high-vol
  tercile, Sharpe=-0.25

## Single-config validation (Step 7), best grid config full-sample (2015-2026)
Params: trend_window=150, credit_zscore_window=80

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **1.01 PASS** | 0.79 FAIL |
| Max Drawdown (<=0.25) | 0.298 **FAIL** | 0.236 PASS |
| TC survival (net Sharpe>=0.5, 10bps/trade) | 0.88 PASS (120 trades) | 0.61 PASS (123 trades) |
| Parameter sensitivity (relative_std<=0.5) | 0.126 PASS (24-combo grid: trend_window∈{100,150,200,250}×credit_zscore_window∈{60,80,100}, both symbols) | (same combined grid) |

Walk-forward not run (same pre-existing `check_walk_forward` infra bug hit
by all iterations this cron trigger).

## Decision
**Reject**, but this is the strongest near-miss of this cron trigger's 4
tested iterations: QQQ actually clears the Sharpe>=1.0 bar (1.01) for the
first time this trigger, though it fails max drawdown (0.298 vs 0.25
threshold -- the 100%-exposure tier during the 2022 rate-hike drawdown
likely drove this). SPY passes MDD but misses Sharpe (0.79). Neither symbol
clears ALL validators simultaneously, so per Step 8's all-validators-pass
rule this is rejected, but it's a materially more interesting candidate than
prior rejects: parameter sensitivity is very low (0.126 over a 24-combo
sweep) and both low+mid vol regimes pass in the grid (broader coverage than
the low-vol-only near-misses earlier this trigger). A future iteration
could test capping the full-exposure tier below 100% (e.g. 80%) specifically
to address QQQ's MDD failure while preserving the Sharpe edge -- flagging
this as a promising direct follow-up.
