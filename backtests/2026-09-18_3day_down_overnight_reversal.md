# Backtest Report: 3 Days Down Overnight Reversal (down_streak=2, hold_days=3)

**Strategy file:** `strategies/2026-09-18_3day_down_overnight_reversal.py`
**Source:** https://www.quantifiedstrategies.com/3-days-down-overnight-trading-strategy/

## Hypothesis

After N consecutive down closes, buy the close and hold for a short fixed
number of bars, on the premise that short-term declines mean-revert. Source's
own headline rule uses a 3-day-down streak with a 1-day overnight hold on
SPY (65% win rate, 8% MDD, 0.13%/trade avg gain), and separately notes an
exit-at-next-close variant with higher avg gain (0.24%) but bigger drawdown
(17%). Source explicitly states the strategy "also works for Nasdaq 100
(QQQ) ... but not as well as for S&P 500" — we found the opposite ranking in
this data window (QQQ passed, SPY didn't), which is noted as a scope
deviation from the source below.

## Step 6 — Grid Test Summary

Grid: `down_streak in [2,3,4]` x `hold_days in [1,2,3]` x equity[SPY,QQQ] x
crypto[BTC/USDT,ETH/USDT], 2015-01-01 to 2026-09-01, vol_regime_splits=3.

- total_cells: 108, passed_cells: 18, **pass_fraction: 0.167**
- by_asset_class: equity 18/54 pass, **crypto 0/54 pass** (decisive fail)
- by_vol_regime: low 5/36, mid 10/36, high 3/36 — mostly a mid-vol-regime edge
- best_cell: equity/QQQ, down_streak=2/hold_days=3, mid-vol Sharpe **2.01**
- worst_cell: equity/QQQ, down_streak=4/hold_days=3, mid-vol Sharpe -0.59

## Step 7 — Single-Config Validation (down_streak=2, hold_days=3)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full sample) | **1.055** ✅ | 0.833 ❌ | ≥1.0 |
| Max Drawdown | 0.202 ✅ | 0.222 ✅ | ≤0.25 |
| TC survival (5bps/trade, net Sharpe) | 0.924 ✅ | 0.676 ✅ | ≥0.5 |
| Parameter sensitivity (rel_std over 3x3 ds/hd grid) | 0.157 ✅ | 0.150 ✅ | ≤0.5 |
| Walk-forward | unavailable in this environment (vectorbt `RangeSplitter` API not present); parameter-sensitivity used as substitute robustness check, per repo convention | | |

Num trades: QQQ 290, SPY 291 (full 2015-2026 sample).

## Decision

**Accept (QQQ only).** All 4 runnable validators pass for QQQ at
down_streak=2/hold_days=3. SPY fails the Sharpe threshold (0.833 < 1.0) —
not accepted, despite passing every other check; source's own SPY-favoring
finding did not replicate in this window/parameterization. Crypto rejected
decisively at the grid stage (0/54 cells).
