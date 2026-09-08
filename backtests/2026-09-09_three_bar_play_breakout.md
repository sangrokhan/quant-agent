# 3 Bar Play Momentum Continuation Breakout — QQQ/SPY/BTC/ETH

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_three_bar_play_breakout.py`
**Outcome:** REJECTED (near-miss on both QQQ and SPY, different validators failing)

## Hypothesis

Per TradingSim's "The 3 Bar Play Pattern: Entry, Stop & Target Rules"
(https://www.tradingsim.com/blog/3-bar-play, fully disclosed): a
wide-range "igniting" bar followed by a tight pullback bar (not exceeding
50% retracement of the igniting bar) signals a low-risk continuation
setup; entry on breakout above the pullback bar's high, stop below its
low. Adapted from intraday (1-2min) to daily bars. First
wide-range-bar + tight-pullback + breakout pattern in this repo, distinct
from NR7/NR4 (narrowest-of-N, no preceding igniting-bar requirement) and
gap-based triggers already tested.

## Grid test (Step 6)

`param_grid`: ignite_range_ratio in [1.3, 1.5, 1.8], pullback_max_pct in
[0.4, 0.5, 0.6]
`symbols`: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
`vol_regime_splits`: 3
Total cells: 108, passed: 14, **pass_fraction: 0.130**

By asset class: equity 14/54, crypto 0/54 (decisive).
By vol regime: low 6/36, mid 3/36, high 5/36 -- fairly evenly spread, no
single dominant regime.

Best average-Sharpe combo (equity): ignite_range_ratio=1.3/pullback_max_pct=0.5
(avg Sharpe 1.059, 3/6 cells pass).
Best single cell: same combo, SPY mid-vol, Sharpe 1.79.

## Single-config validation (Step 7), best config ignite_range_ratio=1.3/pullback_max_pct=0.5

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.791 (FAIL) | 1.244 (PASS) | >= 1.0 |
| Max drawdown | 0.061 (PASS) | 0.027 (PASS) | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.713 net Sharpe (PASS) | 1.089 net Sharpe (PASS) | >= 0.5 |
| Walk-forward (4 splits) | 0.75 (PASS, 3/4) | 1.0 (PASS, 4/4) | >= 0.75 |
| Parameter sensitivity | rel_std 0.296 (PASS) | rel_std 0.551 (FAIL, narrow) | <= 0.5 |

## Decision

**REJECTED overall**, but both symbols are close near-misses on different
validators:
- **QQQ**: fails only Sharpe (0.791 vs 1.0), likely due to low trade
  frequency (19 trades over 7.5yr) -- the pattern is rare on QQQ.
- **SPY**: passes Sharpe/MDD/TC/walk-forward comfortably, fails only
  parameter_sensitivity narrowly (0.551 vs 0.5).

Neither symbol clears the full bar, so this iteration's config is not
accepted. Worth a future targeted refinement (e.g. widening breakout_window
or adjusting max_hold_days, currently fixed at defaults 3/10 and not
grid-swept this iteration) to see if SPY's parameter sensitivity can be
rescued the way 2026-09-09-005 rescued the Monday down-streak QQQ
near-miss, and whether QQQ's trade count can be increased without
sacrificing quality. Crypto rejected decisively (0/54) as expected -- the
igniting-bar + tight-pullback pattern likely gets drowned out by crypto's
generally higher baseline volatility (fewer bars qualify as genuinely
"tight" relative to normal range).

## Source

https://www.tradingsim.com/blog/3-bar-play
