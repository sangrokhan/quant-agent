# Acceleration Bands (Price Headley) Two-Consecutive-Close Breakout — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_acceleration_bands_breakout.py`
**Outcome: REJECTED**

## Hypothesis

Acceleration Bands (Price Headley) are a momentum/breakout-oriented volatility
band (opposite orientation from mean-reversion band systems like Bollinger or
STARC — Acceleration Bands are meant to be *joined* on breakout, not faded).
Per LuxAlgo's Acceleration Bands library page (the only free source disclosing
the exact mechanical rule — quantifiedstrategies.com's numeric rule set is
paywalled):

- `Upper = SMA(High * (1 + 4*(High-Low)/(High+Low)), N)`
- `Lower = SMA(Low  * (1 - 4*(High-Low)/(High+Low)), N)`
- `Midline = SMA(Close, N)`
- Bullish breakout entry: **two consecutive closes** above the Upper Band.
- Exit: the first close back inside the broken Upper Band.

This repo added a `trend_window` SMA gate (0 = off) and a `max_hold_days=20`
time-stop backstop (source specifies neither).

Source: https://www.luxalgo.com/library/indicator/acceleration-bands/ (full
mechanical rule); https://www.quantifiedstrategies.com/acceleration-bands/
(concept background, numeric rules paywalled).

Novelty: first Acceleration Bands strategy in this repo. STARC Bands (tested
twice, both rejected — ids 2026-09-04-146, 2026-09-06-141) use a *mean
reversion* rule off an ATR band; Acceleration Bands are a fundamentally
different momentum/breakout construction off a high/low-range-derived band.

## Step 6 — Grid test

108 cells: `window` [15,20,25] × `trend_window` [0,100,200] × `max_hold_days`
[20], symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3,
2015-2026.

- **pass_fraction: 0.139 (15/108)**
- by_asset_class: equity 15/54 (28%), crypto 0/54 (0%)
- by_vol_regime: low 15/36 (42%), mid 0/36 (0%), high 0/36 (0%)
- best_cell: QQQ, window=25/trend_window=100, **low**-vol slice only, Sharpe 1.917
- worst_cell: QQQ, window=25/trend_window=200, high-vol slice, Sharpe -1.009

The strategy only ever clears the Sharpe/MDD bar within the **low-vol
tercile slice** of equity data — it never passes a single crypto cell, and
never passes mid/high-vol equity cells either.

## Step 7 — Single-config validation (best grid config: window=25,
trend_window=100, max_hold_days=20)

| Symbol | Sharpe (full sample) | MDD | TC-adj Sharpe (10bps, N trades) | Param sensitivity (rel std) |
|---|---|---|---|---|
| QQQ | 0.308 (FAIL, thr 1.0) | 0.178 (PASS, thr 0.25) | 0.161 (FAIL, thr 0.5; 87 trades) | 0.578 (FAIL, thr 0.5) |
| SPY | 0.260 (FAIL, thr 1.0) | 0.084 (PASS, thr 0.25) | 0.033 (FAIL, thr 0.5; 92 trades) | 0.721 (FAIL, thr 0.5) |

Walk-forward: skipped (pre-existing repo-wide `check_walk_forward` bug in the
installed vectorbt version, per prior iterations' notes).

## Decision

**Rejected.** The grid's headline "best cell" Sharpe of 1.92 is an artifact of
slicing to only the low-vol tercile of one symbol/param combo — the
full-sample Sharpe at that exact same config collapses to 0.31 (QQQ) / 0.26
(SPY), decisively missing the 1.0 threshold, and both symbols also fail
transaction-cost survival and parameter sensitivity. MDD is comfortably
within bounds (the strategy is rarely in the market — few, short-duration
breakout trades), but that low exposure is exactly why the low-vol-slice
Sharpe doesn't generalize: most of the strategy's few trades cluster in
low-vol periods, so the "low regime win" is largely just "most of the trades
happened to occur there," not a durable edge that would survive being
isolated and traded on its own. Crypto is unsuitable across the entire grid
(0/54).

## Notes for future loops

If revisiting: the "two consecutive closes above/below" breakout-confirmation
rule is a reasonable no-whipsaw filter but combined with a hard high/low-range
band it produces very few trades (87-92 over 11.7yr) — most breakouts
immediately mean-revert (band walk is rare on QQQ/SPY daily bars), which is
consistent with Acceleration Bands historically being marketed more for
shorter-timeframe/futures/commodities use (Price Headley's original context)
than daily equity ETFs. A shorter-timeframe (1h crypto or intraday equity)
retest, or loosening the two-close confirmation to a single close with an ATR
stop, could be worth trying in a future iteration — but do not just re-widen
the trend_window/max_hold_days grid on daily bars, since the grid here already
covered a reasonably diverse set (9 param combos) without finding a
full-sample-robust config.
