# Backtest Report: A/D Line Bullish Divergence (QQQ)

**Strategy file:** `strategies/2026-09-06_ad_line_bullish_divergence.py`
**Date:** 2026-09-06
**Source:** https://trendspider.com/learning-center/accumulation-distribution-a-d-trading-strategies/

## Hypothesis

Per TrendSpider's A/D guide: "A bullish divergence occurs when the price of
a security is making lower lows, but the A/D line is making higher lows.
This suggests that buying pressure is increasing even though the price is
decreasing, which could signal a potential reversal to the upside."

Entry: local price swing low that is lower than the prior swing low, while
the Chaikin Accumulation/Distribution Line value at that bar is higher than
at the prior swing low. Exit: close crosses back above its N-day SMA, or a
max-hold time-stop.

## Step 6 — Grid test summary (216 cells: 3 swing_window x 2 exit_sma_window
x 3 max_hold_days x 2 asset classes x 2 symbols x 3 vol regimes)

- **Overall pass_fraction: 0.824** (178/216 cells passed Sharpe>=1.0 & MDD<=0.25)
- **By asset class:** equity 73/108 (0.676), crypto 105/108 (0.972)
- **By vol regime:** low 51/72 (0.708), mid 61/72 (0.847), high 66/72 (0.917)
- **Best cell:** swing_window=8, exit_sma_window=20, max_hold_days=10,
  QQQ, high-vol regime, Sharpe=2.96
- **Worst cell:** swing_window=3, exit_sma_window=20, max_hold_days=20,
  SPY, mid-vol regime, Sharpe=-0.55

Both asset classes and all vol regimes clear >0.5 pass fraction; crypto is
notably stronger than equity here (unusual vs. most prior strategies in
this repo, which typically fail crypto decisively).

## Step 7 — Single-config validation (best cell config, QQQ, full sample
2019-01-01 to 2026-09-01)

Config: `swing_window=8, exit_sma_window=20, max_hold_days=10`

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | True | 1.81 | >= 1.0 |
| Max drawdown | True | 0.018 | <= 0.25 |
| TC survival (10bps/trade, 9 trades) | True | net Sharpe 1.77 | >= 0.5 |
| Walk-forward (4-fold, manual split; vbt.utils.splitting unavailable in this vectorbt build) | True | 1.0 pass fraction | >= 0.75 |
| Parameter sensitivity (18-cell QQQ sweep) | True | relative std 0.135 | <= 0.5 |

All 5 validators passed.

## Caveat

Only 9 trades over the ~7.7-year QQQ sample (low signal frequency: bullish
divergence on 8-bar swing lows is a rare pattern) — small trade count means
the Sharpe/MDD numbers have wide statistical uncertainty despite passing
thresholds. Max drawdown is tiny (1.8%) precisely because the strategy is
flat most of the time. Treat as a low-frequency, high-selectivity signal
rather than a core allocation strategy.

## Outcome: **ACCEPTED**

Strategy kept live in `strategies/`. Broad-ish across vol regimes and
(unusually) both asset classes per the grid, and the single best-config
passes all 5 standard validators.
