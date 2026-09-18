# Backtest Report: 123 Pattern Bullish Reversal — Low-Vol Regime-Gated Rescue (QQQ, max_hold_days=30, vol_regime_ratio=0.8)

**Date:** 2026-09-18
**Status:** REJECTED (near-miss on parameter sensitivity)

## Hypothesis

Direct rescue of this same cron trigger's prior rejection 2026-09-18-090
(123 Pattern Bullish Reversal, ungated: SPY full-sample Sharpe 0.79 / MDD
0.31 both failed, but the grid's isolated low-vol tercile showed Sharpe
~2.08 SPY / 1.86 QQQ). This variant adds an explicit low-vol realized-vol
regime gate (20-day realized vol <= `vol_regime_ratio` x trailing 252-day
median, identical construction to
`strategies/2026-09-03_bb_meanrev_qqq_volregime.py`), only taking the
123-pattern entry when the market IS in that low-vol regime.

Source pattern unchanged: https://www.quantifiedstrategies.com/123-pattern-reversal-strategy/

## Step 6 grid summary (`grid_result_123_pattern_reversal_volgate.json`)

- param_grid: `max_hold_days` in [20, 30], `vol_regime_ratio` in [0.8, 1.0]
- symbols: equity (QQQ, SPY), crypto (BTC/USDT, ETH/USDT)
- vol_regime_splits: 3
- **pass_fraction: 0.1875 (9/48 cells)**
- by_asset_class: equity 9/24, crypto 0/24 (decisive crypto reject, unchanged from ungated version)
- by_vol_regime: low 8/16, mid 0/16, high 1/16
- best_cell: QQQ, max_hold_days=30, vol_regime_ratio=0.8, low-vol regime, Sharpe 2.35
- worst_cell: ETH/USDT, max_hold_days=30, vol_regime_ratio=0.8, high-vol regime, Sharpe -1.03

The gate improved the best-cell Sharpe (2.35 vs 2.08 ungated) but did not
change the overall pass_fraction meaningfully (0.1875 vs 0.222) since
crypto remains fully rejected and mid-vol cells still fail.

## Step 7 single-config validation (QQQ, max_hold_days=30, vol_regime_ratio=0.8, full sample 2015-01-01 to 2026-09-01)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | pass | 1.295 | >= 1.0 |
| Max drawdown | pass | 0.110 | <= 0.25 |
| TC survival (10bps/trade, 29 trades) | pass | net Sharpe 1.252 | >= 0.5 |
| Walk-forward (4 splits) | pass | 1.0 pass fraction | >= 0.75 |
| Parameter sensitivity (4-combo grid: max_hold_days x vol_regime_ratio) | **FAIL** | rel_std 0.575 | <= 0.5 |

## Decision: REJECT (near-miss)

Adding the low-vol regime gate successfully rescued the full-sample Sharpe
(0.79 -> 1.29) and max drawdown (0.31 -> 0.11) on QQQ -- the core rescue
hypothesis worked. However, the QQQ parameter-sensitivity sweep across
(max_hold_days, vol_regime_ratio) combinations has relative std 0.575,
just over the 0.5 threshold: performance varies materially between
vol_regime_ratio=0.8 vs 1.0 combined with max_hold_days=20 vs 30 (Sharpes
ranged from 0.86 to 2.35 across the 4-combo QQQ grid), i.e. the gate
threshold itself is not robust to small perturbation. This is a marginal,
fixable near-miss (unlike the ungated version's decisive full-sample fail)
-- a future iteration could retune with a tighter/coarser grid or average
across a small vol_regime_ratio band to reduce sensitivity.

Left `strategies/2026-09-18_123_pattern_reversal_volgate.py` in place as a
record of this near-miss rescue attempt for a future retune iteration.
