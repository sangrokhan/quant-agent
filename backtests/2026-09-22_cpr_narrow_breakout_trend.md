# Backtest Report: Central Pivot Range (CPR) Narrow-Range Breakout + Pivot Trend Exit

**Strategy file:** `strategies/2026-09-22_cpr_narrow_breakout_trend.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-064

## Hypothesis

Per Groww's "Central Pivot Range (CPR): Intraday Trading Strategy Guide"
(https://groww.in/blog/central-pivot-range, read via browser_exec since
`web_search`'s DDGS backend intermittently TLS-errors), CPR is a 3-line
range from the PRIOR period's H/L/C: Pivot P=(H+L+C)/3, Bottom Central
BC=(H+L)/2, Top Central TC=2P-BC. Source: "If the current market price
moves above the top central level, it indicates an uptrend... ideal time
to place buy orders... CPR acts as a support level"; a NARROW CPR
(compressed prior-period range) signals a higher-probability trend day
ahead, per source. Adapted from intraday to daily bars (this repo's
convention for other pivot-family indicators). Long entry: close breaks
above TC AND the CPR is narrow (bottom-40th-percentile width vs. trailing
60-bar history). Exit: close falls back below Pivot P, or max_hold_days
time-stop. First Central Pivot Range strategy in this repo (0 prior KB
hits).

## Grid Test Summary (Step 6)

- Total cells: 48 (2 narrow_pctile x 2 max_hold_days, 3 vol regimes,
  QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.188 (9/48)
- By asset class: equity 6/24, crypto 3/24
- By vol regime: low 9/16, mid 0/16, high 0/16
- Best cell: ETH/USDT, narrow_pctile=0.3/max_hold_days=10, mid-vol regime, Sharpe 1.83
- Worst cell: SPY, narrow_pctile=0.3/max_hold_days=10, mid-vol regime, Sharpe -1.09

## Single-Config Validation (Step 7), narrow_pctile=0.3/max_hold_days=10

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **false** 0.367 | **false** 0.104 | 1.0 |
| Max drawdown | **false** 0.375 | **false** 0.324 | 0.25 |
| Transaction cost survival (10bps/trade) | **false** net Sharpe 0.034 (216 trades) | **false** net Sharpe -0.255 (229 trades) | 0.5 |
| Walk-forward (manual 4-equal-slice) | **false** 2/4 (0.5) | **false** 2/4 (0.5) | 0.75 |
| Parameter sensitivity (4-combo sweep) | true 0.158 | **false** 0.623 | 0.5 |

## Outcome: REJECTED

Decisive rejection on both equity symbols: 4-5 of 5 validators fail on
each. Full-sample Sharpe is weak (0.37 QQQ, 0.10 SPY), max drawdown exceeds
threshold on both (37.5%/32.4%), and the very high trade count (216/229
over ~7.5 years, roughly one trade every 12 trading days) combined with a
10bps/trade cost erodes net Sharpe to near zero or negative -- the
narrow-CPR + TC-breakout entry fires far too often on daily bars to be a
selective, high-conviction trend-day filter the way it is intended
intraday. The grid's isolated low-vol-regime passes (9/16, all other
regimes 0) and one crypto mid-vol outlier cell do not survive full-sample
scrutiny. This is consistent with CPR being fundamentally an INTRADAY tool
(source explicitly frames it for identifying today's likely trend/range
character from yesterday's H/L/C) -- the daily-bar adaptation here loses
the tool's core edge (using it to trade one session ahead) and instead
behaves like an over-frequent daily breakout system. A future iteration
should either source true intraday OHLCV data to test CPR in its native
timeframe, or drop the daily-bar adaptation attempt entirely.
