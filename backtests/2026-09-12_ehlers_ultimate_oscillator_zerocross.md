# Backtest Report: Ehlers Ultimate Oscillator (Dual-Highpass RMS-Normalized) Zero-Cross

**Strategy file:** `strategies/2026-09-12_ehlers_ultimate_oscillator_zerocross.py`
**Date:** 2026-09-12

## Hypothesis

Per John Ehlers' TASC April 2025 article (transcribed with full C code at
https://financial-hacker.com/ehlers-ultimate-oscillator/): the Ultimate
Oscillator is the RMS-normalized difference of two 2-pole highpass filters
(fast period `edge`, slow period `width*edge`), claimed to track market
direction with near-zero lag. Source discloses no explicit trading rule
(pure chart-following visualization); this strategy tests the natural
zero-crossing signal: long when the oscillator crosses from negative to
positive.

## Grid test (Step 6) — `grid_result_ehlers_ultosc.json`

Grid: `edge ∈ {10,20,30}`, `width ∈ {2,3}`, `max_hold_days ∈ {20,40}` ×
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} × vol regime terciles, 2018-01-01
to 2026-09-01. 144 total cells.

- **pass_fraction: 0.2014** (29/144)
- by_asset_class: equity 29/72, **crypto 0/72** (decisive fail)
- by_vol_regime: low 20/48, mid 8/48, **high 1/48**
- best_cell: SPY, `edge=10, width=2, max_hold_days=20`, low-vol, Sharpe 2.25
- worst_cell: QQQ, `edge=30, width=3, max_hold_days=20`, high-vol, Sharpe -0.36

## Full-sample sweep (2018-2026) around the grid's promising region

| Symbol | edge=10,w=2 | edge=20,w=2 | edge=10,w=3 | edge=20,w=3 |
|---|---|---|---|---|
| SPY | 0.791 | 0.599 | 0.736 | 0.570 |
| QQQ | 0.563 | 0.581 | 0.666 | 0.566 |

No configuration reaches the 1.0 Sharpe threshold on the full sample for
either symbol; the grid's promising low-vol-tercile Sharpe (2.25) does not
persist across the full 2018-2026 period.

## Decision

**REJECT for all symbols/asset classes.** Best full-sample Sharpe is SPY
at 0.791 (edge=10, width=2), still below the 1.0 threshold. Did not
proceed to the full validator suite. Crypto rejected decisively at grid
stage (0/72). This is the third Ehlers dual-highpass-family construction
tested with a similar full-sample-vs-low-vol-tercile pattern (grid cells
in low-vol regimes look attractive but don't hold up over the full sample
including 2020/2022 stress periods) -- consistent with the earlier
AutoTune Filter rejection's finding.
