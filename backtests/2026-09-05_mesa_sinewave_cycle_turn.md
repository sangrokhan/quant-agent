# Ehlers MESA Sine Wave Cycle-Turn + EMA Trend Filter — Backtest Report

**Hypothesis:** Ehlers' MESA Sine Wave (homodyne-discriminator dominant-cycle
Sine/LeadSine pair) crossing bullish (Sine crosses above LeadSine while both
are <= 0) while close is above an EMA(trend_window) trend filter marks a
leading cycle-turn long entry; exit on the reverse cross, trend-filter break,
or a max_hold_days time-stop.

**Source:** https://theindicatorlab.com/reviews/ehlers-mesa-sine-wave/
("Wait for Sine Wave (blue) to cross above Lead Sine Wave (red) while both
are below the zero line. Confirm with price breaking above ... a key moving
average (I use 20 EMA)... Take partial profits when Sine Wave crosses below
the Lead Sine Wave.")

**Strategy file:** `strategies/2026-09-05_mesa_sinewave_cycle_turn.py`

## Step 6 — Grid test summary (param_grid: trend_window in [10,20,30] x
max_hold_days in [10,15,20]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 108, passed_cells: 18, **pass_fraction: 0.167**
- by_asset_class: equity 18/54 (33%), crypto 0/54 (0%) — decisive crypto fail
- by_vol_regime: low 18/36 (50%), mid 0/36, high 0/36 — passes ONLY in the
  low-realized-vol tercile
- best_cell: trend_window=20, max_hold_days=10, SPY, low-vol regime,
  Sharpe=1.782
- worst_cell: trend_window=20, max_hold_days=10, QQQ, high-vol regime,
  Sharpe=-0.696

The strategy passes cleanly and consistently across all 3 trend_window
values in the equity low-vol tercile (QQQ Sharpe 1.10-1.35, MDD 0.04-0.06;
SPY Sharpe 1.43-1.78, MDD 0.02-0.03) but is a complete, decisive failure in
mid/high-vol regimes and on both crypto pairs (all 54 crypto cells failed).

## Step 7 — Single-config validators (best grid config: trend_window=20,
max_hold_days=15, full unconditional 2019-2026 sample, NOT restricted to the
low-vol slice)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **FAIL** 0.292 | **FAIL** 0.448 |
| Max Drawdown (<= 0.25) | PASS 0.143 | PASS 0.075 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | **FAIL** 0.083 (66 trades) | **FAIL** 0.185 (70 trades) |
| Parameter sensitivity (relative_std <= 0.5, trend_window in {10,20,30} sweep) | PASS 0.269 | PASS 0.446 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (consistent with other recent entries in this log, e.g.
2026-09-05_vix_vix3m_backwardation_regime.md).

## Outcome: **REJECTED** (unconditional full-period), narrow low-vol-only signal noted

Full, unconditional-sample Sharpe and transaction-cost survival both fail
decisively on both QQQ and SPY — the grid's per-regime breakdown shows this
strategy's entire edge lives in the low-realized-vol tercile (18/18 cells
there pass with Sharpe 1.1-1.8 and tight MDD), while mid/high-vol regimes
and both crypto pairs contribute pure whipsaw losses that swamp the
low-vol edge once averaged over the full sample. This matches the source's
own stated caveat: "Whipsaws badly in choppy, directionless markets." A
future iteration could revisit this exact signal gated by an explicit
low-vol-regime filter (similar to 2026-09-03-001's realized-vol-vs-median
gate) rather than trading it unconditionally.
