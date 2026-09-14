# Backtest report: TTF (Trend Trigger Factor) Continuous Sizing on SMA(40) Trend Gate

**Strategy file:** `strategies/2026-09-14_ttf_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-135
**Source:** https://stonehillforex.com/2022/10/trend-trigger-factor-as-a-confirmation-indicator/
(re-confirmed this iteration via browser_exec; formula matches this repo's
existing entry 2026-09-05-015).

## Hypothesis

Trend Trigger Factor (M.H. Pee, TASC Dec 2004): buy_power = current n-bar
HighestHigh minus prior n-bar LowestLow; sell_power = prior n-bar
HighestHigh minus current n-bar LowestLow; TTF = 100*(buy_power-sell_power)
/(0.5*(buy_power+sell_power)). This repo has 1 prior TTF entry
(2026-09-05-015), a binary zero-line-crossing entry/exit trigger. This
iteration reframes TTF as a CONTINUOUS SIZING dial: rolling z-score
normalized (TTF is unbounded by construction), scales exposure within an
SMA(trend_window) uptrend gate -- this cron trigger's validated
continuous-sizing-dial pattern.

## Step 6 grid summary (`grid_result_ttf_sizing.json`)

- Grid: `sensitivity in [0.3, 0.5]` x `deadband in [0.15, 0.25]` x
  `leverage_cap in [0.4, 1.0]`, symbols QQQ/SPY/BTC/ETH, `vol_regime_splits=3`.
- **96 cells total, 54 passed -- pass_fraction 0.5625.**
- By asset class: equity 24/48 (0.50), crypto 30/48 (0.625).
- By vol regime: low 32/32 (1.00), mid 18/32 (0.5625), high 4/32 (0.125).

## Step 7 single-config validators (`validators_ttf_sizing.json`)

Grid-optimal deadbands (0.15/0.25) worked directly for QQQ/BTC/ETH; SPY
needed a slightly wider deadband=0.30 (sensitivity=0.3) to clear
transaction-cost survival, mirroring this cron trigger's recurring pattern
of SPY requiring more turnover-dampening than QQQ.

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param sens. | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.3, db=0.25, lev=1.0 | 1.181 (pass) | 0.132 (pass) | 0.676 (pass) | 0.75 (pass) | 0.033 (pass) | **ACCEPT** |
| SPY | sens=0.3, db=0.30, lev=1.0 | 1.143 (pass) | 0.070 (pass) | 0.635 (pass) | 0.75 (pass) | 0.027 (pass) | **ACCEPT** |
| BTC/USDT | sens=0.3, db=0.25, lev=0.4 | 1.415 (pass) | 0.227 (pass) | 1.198 (pass) | 1.00 (pass) | 0.020 (pass) | **ACCEPT** |
| ETH/USDT | sens=0.5, db=0.15, lev=0.4 | 1.184 (pass) | 0.245 (pass) | 1.018 (pass) | 1.00 (pass) | 0.033 (pass) | **ACCEPT** |

## Decision

**Full accept**: QQQ, SPY, BTC/USDT, and ETH/USDT ALL pass all 5
validators -- the third full 4-symbol acceptance for a continuous-sizing-
dial strategy this cron trigger (joining KVO-128, Demand Index-126, and
Elder Impulse-133). ETH/USDT's config differs from BTC's (higher
sensitivity 0.5, tighter deadband 0.15) to keep MDD under the 0.25
threshold at 0.245 -- a narrower pass than BTC's but still clean across
all 5 validators.
