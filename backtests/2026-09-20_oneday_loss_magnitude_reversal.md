# One-Day-Loss Magnitude-Scaled Reversal — Backtest Report

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_oneday_loss_magnitude_reversal.py`
**Source:** https://www.quantifiedstrategies.com/one-day-loss-trading-strategy/ (QuantifiedStrategies.com, summarizing a 2003 academic short-term reversal study)

## Hypothesis

Source summarizes an academic study finding that reversal-strategy returns
after large one-day stock losses scale with loss magnitude and are amplified
by high event-day volume. Adapted to this repo's single-symbol daily-bar
interface (no cross-sectional stock universe available): buy the same asset
after its own single-day return drops below a large negative threshold,
optionally gated by above-average volume, hold for a short fixed period.

## Grid test summary (Step 6)

144 cells: `loss_threshold_pct∈{-0.03,-0.05,-0.08} ×
require_high_volume∈{True,False} × max_hold_days∈{3,5}` on equity {QQQ,SPY}
and crypto {BTC/USDT,ETH/USDT}, 3 vol-regime terciles, 2019-01-01 to
2026-09-01.

- **pass_fraction: 0.014 (2/144) — decisive fail**
- by_asset_class: equity 2/72, crypto 0/72
- by_vol_regime: low 0/48, mid 2/48, high 0/48
- best_cell: loss_threshold_pct=-0.03, require_high_volume=False, max_hold_days=3, BTC/USDT, high-vol, Sharpe 1.93 (single narrow slice, not representative)

## Decision: **REJECTED** (decisive — no single-config validation run, grid already conclusive)

Only 2 of 144 grid cells pass, both in equity mid-vol regime slices, with
crypto decisively failing across the board (0/72) despite crypto being
where large single-day drops are most common (the source's own
volume/magnitude-amplification mechanism should, if anything, favor
crypto). The single-symbol adaptation of this cross-sectional academic
finding does not translate to a viable single-asset timing strategy on
daily bars.
