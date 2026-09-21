# Ehlers Smoothed RSI (SRSI) Oversold-Recovery Crossover

**Strategy file:** `strategies/2026-09-22_ehlers_smoothed_rsi_recovery.py`
**Source:** https://www.prorealcode.com/prorealtime-indicators/john-ehlers-smoothed-rsi/
(John Ehlers, "RSI Smoothing" paper), visited 2026-09-22.

## Hypothesis

A 4-tap FIR low-pass filter (binomial weights 1-2-2-1 over 4 bars) applied
to close BEFORE computing Wilder's classic up/down-move RSI produces a
less-jittery oscillator than plain RSI. No trading rule was disclosed by
the source (indicator-comparison chart only); this repo's standard
oversold-recovery-crossover + SMA(200) trend-gate convention was applied.

## Grid test summary (Step 6)

Grid: `oversold_level` in {25, 30, 35} x `max_hold_days` in {5, 10, 15} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 108 cells,
2018-01-01 to 2026-09-01.

- **pass_fraction:** 0.130 (14/108)
- **by_asset_class:** equity 10/54 passed; crypto 4/54 passed
- **by_vol_regime:** low 2/36, mid 5/36, high 7/36 (no strong regime
  concentration, unlike most prior strategies -- mildly favors high-vol)
- **best_cell:** QQQ, oversold_level=25, max_hold_days=10, mid-vol regime,
  Sharpe 1.61

## Full-period single-config validation (Step 7)

Wider manual sweep (`oversold_level` in {20,25,30,32,35,38,40},
`max_hold_days` in {3,5,7,10,12,15,20}, `rsi_window` in {10,14,20}) found
**no QQQ full-period config clears Sharpe 0.9**, but SPY clears at
`oversold_level=35, max_hold_days=10`:

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (SPY) | 1.057 | 1.0 | pass |
| Max drawdown (SPY) | 0.061 | 0.25 | pass |
| Transaction cost survival (SPY, 10bps/trade, 167 trades) | 0.250 | 0.5 | **FAIL** |

Net-of-cost Sharpe (0.250) is far below the 0.5 threshold -- decisive fail,
not a near-miss. Checked neighboring configs (oversold 35-40, hold 10-20):
TC-survival net Sharpe never exceeds 0.25, and gets worse (even negative)
at higher oversold thresholds despite raw Sharpe looking fine at
oversold=38. Stopped here (walk-forward/parameter-sensitivity not run)
since TC-survival is a decisive, non-marginal fail.

## Decision

**REJECTED.** QQQ fails full-period Sharpe decisively across the entire
parameter sweep tried. SPY clears raw Sharpe/MDD at one config but fails
transaction-cost survival decisively (net Sharpe 0.25 vs 0.5 threshold) --
the strategy trades too frequently (167 trades over 8.7yr) relative to its
edge to survive realistic costs. Not a near-miss worth a targeted rescue
attempt given how far below threshold both symbols land.
