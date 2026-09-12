# 2026-09-13: TQQQ "One Percent A Week" dip-entry (base TASC 2026.03 variant)

**Hypothesis (id 2026-09-13-001):** TASC March 2026 Traders' Tips "A
High-Probability Weekly Trading Strategy For TQQQ" base variant
(https://www.tradingview.com/script/nVECqIQx-TASC-2026-03-One-Percent-A-Week/):
each week, set a limit buy 1% below Monday's open; if filled, set a 1%
take-profit starting the next bar, a breakeven stop once a 0.5% drawdown
from fill is observed, and a hard Friday-close exit regardless. Distinct
from the already-tested ADAPTIVE variant (2026-09-12-145,
`2026-09-12_tqqq_adaptive_weekly_momentum_exit.py`) which enters
unconditionally at Monday's open with a momentum-scaled 7%/1.5%
target/stop and a Tuesday fade-exit -- this base variant instead uses a
conditional limit-order dip entry (may skip weeks) with a fixed 1%/1%
target and no target-widening.

## Grid test (Step 6)

`run_strategy_grid`, params `dip_pct in [0.005,0.01,0.015]`, `target_pct in
[0.01,0.015]`, `breakeven_dd_pct=0.005`, symbols equity=[TQQQ,QQQ]
crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.0 (0/72 cells)** -- decisive fail across every
  asset/param/vol-regime combination.
- by_asset_class: equity 0/36, crypto 0/36.
- by_vol_regime: low 0/24, mid 0/24, high 0/24.
- best_cell: equity/QQQ/low-vol, dip_pct=0.005/target_pct=0.015, Sharpe
  0.915 (still below the 1.0 threshold).
- worst_cell: equity/QQQ/mid-vol, dip_pct=0.01/target_pct=0.015, Sharpe
  -1.567.

## Single-config check (best-looking config, full sample, TQQQ itself)

`dip_pct=0.005, target_pct=0.015, breakeven_dd_pct=0.005`, TQQQ 2019-01-01
to 2026-09-01 (n≈1309 nonzero-return bars):

- Sharpe: **-0.295** (threshold 1.0) -- FAIL
- Max drawdown: **0.960** (threshold 0.25) -- FAIL (TQQQ's own 3x-leveraged
  drawdowns overwhelm the strategy's tight 1%/1% stop-target box; frequent
  small dip-entries during TQQQ's 2022 leveraged-ETF decay period compound
  heavy losses that the breakeven stop cannot always catch given only
  daily-bar OHLC resolution).

No walk-forward/transaction-cost/parameter-sensitivity validators run --
grid pass_fraction 0.0 is decisive and matches this repo's convention of
skipping the full single-config validator suite when the grid itself is
conclusively negative (see e.g. 2026-09-12-193, 2026-09-12-207).

## Outcome: REJECTED (decisive)

The 1%-dip / 1%-target box is far too tight relative to TQQQ's realized
daily-bar volatility (even at the low-vol tercile), and the daily-bar
data resolution can't reliably enforce the breakeven-stop before a much
larger adverse move prints within the same bar -- unlike the already-
accepted-for-SPY-only adaptive variant (2026-09-12-145), whose wider
7%/1.5% target/stop and unconditional Monday-open entry tolerate daily-bar
approximation much better. Source URL:
https://www.tradingview.com/script/nVECqIQx-TASC-2026-03-One-Percent-A-Week/
