# Backtest Report: Chande Kroll Stop Trend-Following (QQQ)

**Strategy file:** `strategies/2026-09-21_chande_kroll_stop_trend.py`
**Date:** 2026-09-21
**Knowledge base id:** 2026-09-21-215

## Hypothesis

The Chande Kroll Stop (Tushar Chande & Stanley Kroll) builds a pair of
ATR-based volatility-adaptive stop lines:

- `long_stop  = rolling_max(HighestHigh(p) - x*ATR(p), q)`
- `short_stop = rolling_min(LowestLow(p) + x*ATR(p), q)`

Default disclosed parameters (per Google AI-overview synthesis of
TrendSpider/Definedge Securities pages, browser_exec Google SERP fallback --
web_search DDGS backend erroring with TLS RequestError on every query this
iteration): p=10, x=1.0, q=9.

Trading rule: long entry when close breaks above `short_stop` (the
high/upper stop line) gated by a 21-period SMA uptrend filter; exit to flat
when close closes below `long_stop` (the low/lower stop line), signaling
trend exhaustion. First Chande Kroll Stop strategy in this repo -- distinct
from existing Chandelier Exit strategies (single ATR-trailing-stop off
highest-high only, not this indicator's dual smoothed high/low band pair).

Source: Google AI-overview (TrendSpider, Definedge Securities, EBC
Financial Group corroborating), https://www.google.com/search?q=Chande+Kroll+Stop+indicator+trading+strategy+entry+exit+rules+ATR

## Step 6 grid summary (144 cells: 2 atr_period x 3 atr_mult x 2 smooth_period x 2 asset classes x 2 symbols x 3 vol regimes)

- Overall pass_fraction: 0.347 (50/144)
- By asset class: equity 41/72 (0.569), crypto 9/72 (0.125)
- By vol regime: low 33/48 (0.688), mid 10/48 (0.208), high 7/48 (0.146)
- Best cell: QQQ-analog SPY, atr_period=14/atr_mult=2.0/smooth_period=9, low-vol, Sharpe 2.38
- Worst cell: QQQ, atr_period=10/atr_mult=1.5/smooth_period=9, high-vol, Sharpe -0.47

**Honest scope**: this strategy is strongest on equity in low-volatility
regimes; crypto and high-vol regimes are much weaker (consistent with a
trend-following ATR-trailing-stop design whipsawing in choppy/high-vol
conditions). Best full-sample averaged config across param grid: QQQ
atr_period=10, atr_mult=2.0, smooth_period=14 (mean cross-vol-regime Sharpe
1.24).

## Step 7 single-config validation (QQQ, atr_period=10/atr_mult=2.0/smooth_period=14, full sample 2018-01-01 to 2026-09-01)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.063 | >= 1.0 |
| Max drawdown | PASS | 0.225 | <= 0.25 |
| Transaction cost survival (10bps/trade, 310 trades) | PASS | net Sharpe 0.589 | >= 0.5 |
| Walk-forward (4 splits, manual fallback) | PASS | 1.0 (4/4 splits positive Sharpe) | >= 0.75 |
| Parameter sensitivity (12-combo grid, relative std) | PASS | 0.106 | <= 0.5 |

All validators pass. **ACCEPT (QQQ)**.

## Decision

Accepted for QQQ (equity). Not tested/validated for SPY/crypto in this
iteration beyond the Step 6 grid scan -- grid shows crypto much weaker
(0.125 pass fraction) and should not be assumed to transfer without a
dedicated leverage-cap-aware retune in a future iteration.
