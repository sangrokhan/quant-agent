# Bullish Wolfe Wave 5-Swing Reversal — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_wolfe_wave_bullish_reversal.py`
**Knowledge base id:** 2026-09-09-048

## Hypothesis

Per Investopedia's Wolfe Wave guide
(https://www.investopedia.com/terms/w/wolfewave.asp) and Dhan.co's
operational writeup (https://dhan.co/blog/technical-analysis/wolfe-wave-pattern/),
a bullish Wolfe Wave is a 5-swing-point pattern forming during a downtrend:
alternating swing lows/highs L1-H2-L3-H4-L5, where wave 3 extends beyond
wave 1, wave 5 makes a lower low than wave 3 (overshoot), and the upper
trendline (H2-H4) converges. After confirmation that buyers regain control
following L5, price is expected to reverse toward the "Estimated Price at
Arrival" (EPA) target -- the line connecting waves 1 and 4, extrapolated
forward.

Daily-bar approximation implemented here: `scipy.signal.argrelextrema`
pivot detection (symmetric window), pattern-matching on the alternating
L-H-L-H-L sequence with the channel/overshoot price constraints, entry on
close crossing back above its short rolling mean after L5 (confirmation
proxy), exit at EPA target, stop-loss at L5's low, or a `max_hold_days`
time-stop.

First Wolfe-Wave-family strategy in this repo (no prior Wolfe/Elliott-wave
entries in `strategies_index.jsonl`).

## Source URLs (visited this iteration)

- https://www.buildalpha.com/opening-range-breakout/ (ORB fade guide -- explored first, not used; too generic for a testable daily-bar hypothesis, intraday-only)
- https://www.investopedia.com/terms/w/wolfewave.asp
- https://dhan.co/blog/technical-analysis/wolfe-wave-pattern/

## Step 6 grid test summary

Grid: `pivot_window` in {4,5,7} x `max_hold_days` in {15,25} x
{QQQ, SPY, BTC/USDT, ETH/USDT} x low/mid/high vol terciles, 72 cells,
2018-01-01 to 2024-12-31.

- **pass_fraction:** 0.194 (14/72)
- **by_asset_class:** equity 14/36, crypto 0/36 (decisive -- crypto out of scope)
- **by_vol_regime:** low 0/24, mid 6/24, high 8/24 (edge concentrated in mid/high vol)
- **best_cell:** pivot_window=7, max_hold_days=25, QQQ, mid-vol, Sharpe=2.06
- **worst_cell:** pivot_window=5, max_hold_days=15, ETH/USDT, low-vol, Sharpe=0.04

## Step 7 single-config validation (primary config: pivot_window=5, max_hold_days=25)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 1.051 | 1.268 | >= 1.0 | Yes (both) |
| Max drawdown | 0.122 | 0.059 | <= 0.25 | Yes (both) |
| Net Sharpe after costs (10bps/trade, 12 trades) | 1.026 | 1.235 | >= 0.5 | Yes (both) |
| Walk-forward pass fraction (manual 4-split, vectorbt's `RangeSplitter` unavailable in installed version) | 1.0 (4/4) | 1.0 (4/4) | >= 0.75 | Yes (both) |
| Parameter sensitivity (relative std across 6-cell QQQ sweep) | 0.285 | -- | <= 0.5 | Yes |

Note: `validators.check_walk_forward` raised `AttributeError:
module 'vectorbt.utils' has no attribute 'splitting'` with the installed
vectorbt version -- substituted a manual 4-equal-split walk-forward
(same pass/fail contract: fraction of splits with positive Sharpe) rather
than skip the check. Flagging this vectorbt API mismatch for a future
loop to fix in `validation/validators.py`.

## Decision: **ACCEPT**

All validators for the primary config (pivot_window=5, max_hold_days=25)
pass on both QQQ and SPY. Trade frequency is low (12 trades over ~7 years
per symbol), consistent with the pattern's rarity requirement (a full
5-point alternating swing structure with geometric constraints).
Crypto is decisively out of scope (0/36 grid cells) -- strategy validity
is equity-only in this repo's finding. Scope recorded honestly in the
knowledge base entry's `symbols`/`notes`.
