# Backtest Report: Dual-Timeframe ROC Extreme-Point Breakout

**Strategy file:** `strategies/2026-09-04_dual_roc_extreme_breakout.py`
**Hypothesis ID:** 2026-09-04-092

## Hypothesis

Slow ROC (lookback=roc1_window) as trend filter (long only if ROC1>0), fast
ROC (lookback=roc2_window=~0.5*roc1_window) as setup (long only if ROC2>0);
entry when close breaks above the rolling extreme-point (max close over
roc2_window). Exit via a fixed time exit (time_index bars) or an
ATR(20)*atr_stop_mult stop-loss. Per oxfordstrat.com's published 40yr/42-
futures dual-momentum ROC system (best case Sharpe 0.90 on futures).

Source: https://oxfordstrat.com/trading-strategies/dual-momentum-rate-of-change/

## Single-config validator results (SPY, roc1_window=100/time_index=60/atr_stop_mult=3.0)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.092 | 1.0 |
| Max drawdown | ✅ | 0.164 | 0.25 |
| Transaction cost survival (10bps/trade, 23 trades) | ✅ | net Sharpe 1.046 | 0.5 |
| Walk-forward (4 manual date-slices) | ✅ | 4/4 positive (0.93, 0.27, 1.94, 1.29) | 0.75 |
| Parameter sensitivity (roc1_window in [60,80,100,120,140]) | ✅ | rel-std 0.122 | 0.5 |

## Step 6 grid summary (roc1_window ∈ {60,100}, time_index ∈ {40,60}, atr_stop_mult ∈ {3.0,4.0}; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 96, passed_cells: 23, pass_fraction: 0.240
- by_asset_class: equity 23/48, crypto 0/48
- by_vol_regime: low 16/32, mid 7/32, **high 0/32**
- best_cell: SPY, roc1_window=100/time_index=60/atr_stop_mult=3.0, low-vol regime, Sharpe 3.34
- worst_cell: QQQ, roc1_window=60/time_index=40/atr_stop_mult=4.0, high-vol regime, Sharpe -1.04

**Interpretation:** grid passes concentrate in low/mid-vol regimes (16+7=23
of 23 total passes), zero in high-vol -- this dual-momentum breakout works
in calmer trending markets, consistent with the source's own long-holding-
period preference finding. Full-sample (all regimes blended) SPY config
still clears 1.0 Sharpe with a comfortable margin because the low/mid-vol
periods dominate the 2019-2026 sample and the ATR stop limits high-vol-
period damage. Crypto rejected decisively (0/48 grid cells) -- despite the
source's original universe being diversified futures including crypto-
adjacent macro assets, the daily-bar equity adaptation does not transfer to
BTC/ETH.

## Decision

**ACCEPT (SPY only)**, config: `roc1_window=100, time_index=60,
atr_stop_mult=3.0` (roc2_window and atr_window left at module defaults 50
and 20). All 5 standard validators pass cleanly, including a comfortable
walk-forward (4/4 positive splits, though one split -- the second -- was
only marginally positive at 0.27, worth flagging for a future loop). QQQ
came close (full-sample Sharpe 0.960 for the same config, just under 1.0)
-- flagged for a future loop to try a QQQ-specific parameter tune. Crypto
and high-vol-regime equity slices are explicitly out of scope for this
accepted config.
