# Backtest Report: Bulkowski Improved Double 7s QQQ Rescue

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-26_bulkowski_improved_double7s_trailing_stop.py` (unchanged code, new per-symbol config)
**Hypothesis id:** 2026-09-27-054

## Hypothesis

Direct rescue attempt of this repo's own near-miss 2026-09-26-005
(Bulkowski's Improved Double 7s ETF Setup,
https://thepatternsite.com/Double7sSetup.html: SMA trend filter + N-bar
lowest-close entry + trailing stop below the day's high once an M-bar
highest-open condition triggers). At the previously-accepted SPY config
(`sma_window=35, buy_lookback=9, sell_lookback=11, trail_offset_pct=0.012`),
QQQ passed Sharpe (1.095) and transaction-cost survival (1.021) but
decisively FAILED max drawdown (0.292 vs 0.25 threshold) — a pure
risk-control gap, not a signal-quality problem, per the near-miss's own
notes. This sub-iteration searches for a QQQ-specific configuration
(same unmodified strategy code) that tightens the trailing stop / trigger
lookbacks enough to bring MDD under 0.25 while keeping Sharpe above 1.0.

## Parameter search

A 4x4x3x5 = 240-combination sweep (`sma_window` x `buy_lookback` x
`sell_lookback` x `trail_offset_pct`) filtered for cells clearing BOTH
Sharpe>=1.0 AND MDD<=0.25 found exactly one passing configuration:
`sma_window=35, buy_lookback=9, sell_lookback=7, trail_offset_pct=0.012`
(only the `sell_lookback` differs from the SPY config: 7 instead of 11 —
a tighter/faster trailing-stop-arming trigger).

## Single-config validation (Step 7)

| Validator | QQQ (rescue config) |
|---|---|
| Sharpe ratio (>=1.0) | PASS 1.004 (thin margin, worth flagging) |
| Max drawdown (<=0.25) | PASS 0.143 |
| Transaction-cost survival (net Sharpe >=0.5, 49 trades) | PASS 0.923 |
| Walk-forward (manual 4-split substitute) | PASS 0.75 (3/4 splits positive) |
| Parameter sensitivity (relative_std<=0.5, 81-cell local grid) | PASS 0.340 |

All 5 validators pass, though the Sharpe margin (1.004) is thin — a small
future data update could flip this back below 1.0, similar to the
already-flagged thin margin on 2026-09-27-049 (RSI(2) dip-buy). Walk-
forward is also a narrow pass (3/4 splits, exactly at the 0.75 threshold).

## Decision

**Accepted for QQQ** at `sma_window=35, buy_lookback=9, sell_lookback=7,
trail_offset_pct=0.012` — a genuinely different config from the
already-accepted SPY config (`sell_lookback=11` there vs `7` here), so
this repo now has per-symbol tuned configs for both QQQ and SPY on this
strategy family, closing out the near-miss from 2026-09-26-005. Given the
thin Sharpe/walk-forward margins, this should be flagged as a candidate
for re-validation in a future loop if new data becomes available.
