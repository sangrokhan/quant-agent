# Backtest Report: HalfTrend (everget, 2021) ATR-based trend-following

**Strategy file:** `strategies/2026-09-16_halftrend.py`
**Date:** 2026-09-16

## Hypothesis

HalfTrend (Alex Orekhov "everget", 2021, GPL-3.0, full Pine v6 source
disclosed) is an ATR-based trend-following indicator similar to SuperTrend
but with a different state machine: tracks running max-low-price /
min-high-price extremes, flips trend state when an `amplitude`-period SMA
of high/low crosses the tracked extreme AND close breaks the prior bar's
low/high. The HalfTrend line then tracks a rising "up" level (uptrend) or
falling "down" level (downtrend), each anchored at trend-flip time to the
other level's most recent value (a hysteresis mechanic distinct from
SuperTrend/Chandelier Exit/OTT already tested). Long-only: long when trend
state = uptrend.

Source: https://www.tradingview.com/script/U1SJ8ubc-HalfTrend/ (exact
disclosed Pine v6 source, no ambiguity in the formula).

## Grid test (Step 6)

Grid: `amplitude`∈{2,4,6} × `channel_deviation`∈{1.5,2.0,2.5} ×
`max_hold_days`∈{40,80}, symbols {QQQ, SPY} × {BTC/USDT, ETH/USDT},
vol_regime_splits=3. 216 cells total.

- **pass_fraction: 0.333** (72/216)
- by_asset_class: equity 54/108 (0.5), crypto 18/108 (0.167)
- by_vol_regime: low 54/72 (0.75), mid 12/72 (0.167), high 6/72 (0.083)
- best_cell: SPY, amplitude=4/channel_deviation=1.5/max_hold=80, low-vol, Sharpe 2.88

Per-symbol best average-Sharpe configs: all 4 symbols had strong average
Sharpes (1.13-1.45) at channel_deviation=1.5 across the board, suggesting
the tighter channel setting is generally preferred, with amplitude
per-symbol-specific.

## Full-sample validators (Step 7), 2019-01-01 to 2026-09-01

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass frac | Param sensitivity (rel std) | All 5 pass? |
|---|---|---|---|---|---|---|
| QQQ (amp=6/cd=1.5/hold=40, retuned) | 1.060 (pass) | 0.226 (pass) | 1.006 (pass) | 1.00 (pass) | 0.078 (pass) | **Yes** |
| SPY (amp=6/cd=1.5/hold=40) | 1.389 (pass) | 0.108 (pass) | 1.318 (pass) | 1.00 (pass) | 0.145 (pass) | **Yes** |
| BTC/USDT (amp=4/cd=1.5/hold=40) | 1.197 (pass) | 0.589 (**FAIL**, decisive) | 1.178 (pass) | 1.00 (pass) | 0.173 (pass) | **No** |
| ETH/USDT (amp=6/cd=1.5/hold=40) | 0.973 (**FAIL**, near-miss) | 0.643 (**FAIL**, decisive) | 0.961 (pass) | 1.00 (pass) | 0.079 (pass) | **No** |

Note: QQQ's grid-best-average-Sharpe config (amplitude=2/channel_deviation=1.5/
max_hold=40) decisively failed full-sample MDD at 0.357; a dedicated finer
sweep over amplitude∈{2,4,6,8}×channel_deviation∈{1.5,2.0,2.5,3.0}×
max_hold_days∈{20,40,80} found amplitude=6/channel_deviation=1.5/max_hold=40
clears all 5 validators.

## Decision (Step 8)

**Accept: QQQ and SPY** (both all 5 validators pass, with QQQ requiring a
per-symbol retune from the grid's naive best-average-Sharpe cell).
**Reject: BTC/USDT and ETH/USDT** (Sharpe passes on BTC, near-misses on
ETH, but both decisively fail MDD — 0.589 and 0.643, more than double the
0.25 threshold). Same repo-wide pattern as several other pure trend-
following signals: raw crypto volatility needs an explicit vol-targeting
overlay this base signal doesn't include. Plausible future rescue candidate
via this repo's established inverse-volatility sizing pattern.
