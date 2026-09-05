# ZigZag Higher-High Breakout Trend Continuation — REJECTED

**Strategy file:** `strategies/2026-09-05_zigzag_higher_high_breakout.py`
**Knowledge base id:** 2026-09-05-089
**Source:** https://www.thinkmarkets.com/en/indicators-and-patterns/zigzag-indicator/

## Hypothesis

ZigZag pivot detection (percentage-deviation-filtered swing highs/lows):
a newly-confirmed pivot high exceeding the previous confirmed pivot high
(higher-high breakout) signals trend continuation worth a long entry;
exit on a lower-low pivot breakdown or a time-stop. First ZigZag-based
strategy in this repo.

## Grid test summary (72 cells: equity QQQ/SPY + crypto BTC/ETH, params
deviation_pct in {0.05, 0.08, 0.10} x max_hold_days in {20, 30},
vol_regime_splits=3)

- pass_fraction: **0.0 (0/72)** -- decisive rejection, no near-misses
- by_asset_class: equity 0/36, crypto 0/36
- by_vol_regime: low 0/24, mid 0/24, high 0/24
- best_cell: BTC/USDT low-vol, deviation_pct=0.10, Sharpe -0.361 (still
  negative)
- worst_cell: SPY low-vol, deviation_pct=0.05, Sharpe -2.494

## Verdict: REJECTED

Every single grid cell across both asset classes and all three
volatility regimes produced a negative or near-zero Sharpe ratio -- the
worst full rejection observed in this session (best cell across the
entire grid was still negative). The higher-high pivot breakout entry
appears to buy near local tops rather than capturing genuine trend
continuation on this daily-bar universe; the percentage-deviation pivot
confirmation introduces significant lag (a pivot only confirms after
price has already retraced deviation_pct from the extreme), likely
entering well after the breakout has already run and exited.
