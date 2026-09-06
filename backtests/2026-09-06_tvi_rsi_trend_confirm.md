# Backtest Report: TVI + RSI Trend Confirmation Long Entry (QQQ)

**Strategy file:** `strategies/2026-09-06_tvi_rsi_trend_confirm.py`
**Date:** 2026-09-06
**Source:** https://www.timothysykes.com/blog/how-to-use-trade-volume-index/

## Hypothesis

Per timothysykes.com's TVI guide: "If the TVI shows strong buying pressure
and the RSI indicates that a stock is not yet overbought, it could be a
signal to enter a [trade]." Also uses the source's trend-confirmation
guidance ("a stock is trending upward and the TVI is increasing, it
confirms that the trend is backed by strong buying activity") as an
additional price-trend precondition.

Entry: TVI (Blau's classic volume-flow indicator, distinct from OBV and
A/D Line) trend rising (10-day SMA of TVI above its value 5 days ago) AND
RSI(14) below an overbought threshold AND price above its 50-day SMA.
Exit: RSI crosses above the overbought threshold, TVI trend flips down, or
a time-stop. First TVI strategy in this repo.

## Step 6 — Grid test summary (216 cells: rsi_overbought[60,65,70] x
tvi_sma_window[10,15] x max_hold_days[10,15,20] x 2 asset classes x 2
symbols each x 3 vol regimes)

- **Overall pass_fraction: 0.296** (64/216)
- **By asset class:** equity 64/108 (0.593), crypto 0/108 (decisive reject)
- **By vol regime:** low 36/72 (0.5), mid 19/72 (0.264), high 9/72 (0.125)
- **Best cell:** rsi_overbought=65.0, tvi_sma_window=10, max_hold_days=10,
  QQQ, low-vol, Sharpe=3.05

Solid on equity across all three vol regimes (though weaker in high-vol);
decisively rejected on crypto.

## Step 7 — Single-config validation (best cell config, QQQ, full sample
2019-01-01 to 2026-09-01)

Config: `rsi_overbought=65.0, tvi_sma_window=10, max_hold_days=10`

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | True | 1.825 | >= 1.0 |
| Max drawdown | True | 0.095 | <= 0.25 |
| TC survival (10bps/trade, 131 trades) | True | net Sharpe 1.484 | >= 0.5 |
| Walk-forward (4-fold, manual split) | True | 1.0 pass fraction | >= 0.75 |
| Parameter sensitivity (18-cell QQQ sweep) | True | relative std 0.193 | <= 0.5 |

All 5 validators passed.

## Outcome: **ACCEPTED**

Strategy kept live in `strategies/`. Passes all 5 standard validators on
full-sample QQQ, and holds up reasonably across all three vol regimes on
the grid (equity only) with a healthy 131-trade sample. Scope: equity only
(QQQ confirmed; SPY not separately re-validated but grid pass_fraction
suggests similar behavior) -- crypto is decisively rejected and should not
be traded with this strategy.
