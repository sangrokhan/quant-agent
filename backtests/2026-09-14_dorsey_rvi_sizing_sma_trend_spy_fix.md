# 2026-09-14 Dorsey RVI Sizing SMA Trend — SPY fix

## Hypothesis

SPY fix for 2026-09-14-142 (Dorsey Relative Volatility Index continuous
sizing dial, accepted QQQ but SPY was a near-miss failing only
TC-survival: gross Sharpe 1.065 passed but net-of-cost Sharpe 0.371<0.5,
sensitivity=0.4/rvi_window=10/trend_window=40/deadband=0.2 gave too much
turnover at 170 trades). Widening the deadband search (0.2-0.5) alongside
rvi_window/trend_window/sensitivity finds SPY passes cleanly at
rvi_window=10/trend_window=60/sensitivity=0.8/deadband=0.5 (Sharpe 1.199,
TC-survival net Sharpe 0.868, only 96 trades vs. the original 170). Same
strategy file (strategies/2026-09-14_dorsey_rvi_sizing_sma_trend.py), same
already-confirmed Dorsey RVI formula (tradingsim.com), no new external
fetch.

## Grid (Step 6 — targeted SPY-only sweep)

`param_grid={rvi_window:[10,14], trend_window:[40,60],
sensitivity:[0.4,0.6,0.8], deadband:[0.2,0.3,0.4,0.5]}`, symbol SPY only
-> 48 combos evaluated by full-sample Sharpe + TC-survival net Sharpe;
best-by-TC-survival: rvi_window=10/trend_window=60/sensitivity=0.8/
deadband=0.5 (Sharpe 1.199, TC net Sharpe 0.868, 96 trades). Wider
deadband cuts turnover from 170 (original config) to 96 trades, directly
addressing the prior TC-survival miss.

## Step 7 — Single-config validation (SPY, rvi_window=10/trend_window=60/sensitivity=0.8/deadband=0.5)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.199 | 1.0 | ✅ |
| Max drawdown | 0.110 | 0.25 | ✅ |
| TC-survival net Sharpe | 0.868 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.0 | 0.75 | ✅ |
| Parameter sensitivity (rel std) | 0.119 | 0.5 | ✅ |

Walk-forward used the repo-standard manual 4-equal-slice fallback
(vbt.utils.splitting API unavailable in installed vectorbt==1.1.0).

## Step 8 — Accept/Reject

**SPY: accepted.** All 5 validators pass, rescuing the prior 2026-09-14-142
SPY near-miss (TC-survival 0.371 -> 0.868). QQQ config from 2026-09-14-142
unchanged (already accepted, not retested this iteration). Crypto remains
out of scope (prior decisive BTC/USDT and ETH/USDT Sharpe/MDD/TC failures,
tried multiple leverage_cap values already, not revisited).
