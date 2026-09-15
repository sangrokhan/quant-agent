# Backtest Report: GAPO Inverse-Volatility Sizing — QQQ Sharpe Fix (Wider Param Search)

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-14_gapo_invvol_sizing_sma_trend.py` (unchanged)
**Knowledge base id:** 2026-09-16-107

## Hypothesis

Direct fix for prior id 2026-09-14-137 (Gopalakrishnan Range Index
(GAPO) as an INVERSE volatility-conditioning multiplier, min-max
normalized within an SMA(trend_window) uptrend gate; accepted SPY
[narrow], BTC/USDT, ETH/USDT, but QQQ rejected -- "Sharpe below 1.0
threshold across base_exposure/sensitivity/deadband sweep"). This
sub-iteration widens the parameter search to also vary trend_window,
gapo_period, and norm_window (not just base_exposure/sensitivity/
deadband as in the original grid) on the identical unmodified GAPO
strategy code. No new external research this sub-iteration (same
formula source as 2026-09-14-137, StockSharp docs).

## Validation (QQQ retune)

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.279 | 0.155 | 0.885 | 0.75 | 0.039 | PASS |

QQQ now passes all 5 validators at trend_window=50/gapo_period=10/
norm_window=180/sensitivity=0.8/deadband=0.20 (vs prior default
trend_window=40/gapo_period=14/norm_window=252).

## Outcome

**Accepted — QQQ**. Combined with the existing SPY/BTC-USDT/ETH-USDT
accept from 2026-09-14-137, GAPO inverse-volatility sizing dial now
covers the full universe (QQQ, SPY, BTC/USDT, ETH/USDT).
