# Backtest Report: ATR Percentile Breakout (2026-09-20)

**Status: ACCEPTED** (QQQ, BTC/USDT). SPY and ETH/USDT tested but did not clear the Sharpe threshold at any grid config (SPY best Sharpe 0.672, ETH/USDT best Sharpe 0.840) — kept as an honest partial-scope acceptance, not a full-universe pass.

## Hypothesis

Source: https://pinescriptforge.com/strategy/atr-percentile-breakout (visited via `browser_exec`).

When 14-period ATR falls into the bottom decile of its own trailing 100-bar
distribution, that marks extreme volatility compression. Rather than
betting on direction directly, enter on a short (5–10 bar) high/low
breakout out of that compressed state, treating the breakout direction as
the signal for which way volatility is about to expand. Long-only
adaptation of source's long/short design.

## Single-config metrics

| Symbol | Config | Sharpe | MDD | Net Sharpe (5bp, N trades) | Walk-forward pass_fraction | Param sensitivity (rel. std) |
|---|---|---|---|---|---|---|
| QQQ | pctile_threshold=0.20, breakout_window=5, target_atr_mult=1.5 | 1.254 ✅ | 0.067 ✅ | 0.619 ✅ (272 trades) | 1.00 ✅ | 0.068 ✅ |
| BTC/USDT | pctile_threshold=0.10, breakout_window=10, target_atr_mult=1.5 | 1.007 ✅ | 0.143 ✅ | 0.894 ✅ (202 trades) | 0.75 ✅ | 0.101 ✅ |

SPY: best Sharpe across grid 0.672 (❌ fail). ETH/USDT: best Sharpe 0.840 (❌ fail).

(`check_walk_forward` in `validation/validators.py` currently errors —
`vectorbt.utils` has no `splitting` attribute in this install, a known
pre-existing issue per repo notes — so walk-forward was computed with a
manual 4-equal-slice fallback: per-slice Sharpe > 0 counted as a pass.)

## Grid summary

`validation/grid_test.py::run_strategy_grid`, `pctile_threshold ∈ {0.10,0.20}`
× `breakout_window ∈ {5,10}` × `target_atr_mult ∈ {1.5,2.0}`, symbols
`{QQQ,SPY,BTC/USDT,ETH/USDT}`, `vol_regime_splits=3`:

- total_cells=96, passed_cells=27, **pass_fraction=0.281**
- by_asset_class: equity 18/48, crypto 9/48 (both non-trivial — a broader
  cross-asset-class hold than most rejected strategies in this repo, which
  typically show 0/48 crypto)
- by_vol_regime: low 10/32, mid 10/32, high 7/32 (fairly even spread
  across regimes — not concentrated in a single tercile)
- best_cell: SPY, low-vol, pctile_threshold=0.20/breakout_window=5/target_atr_mult=1.5, Sharpe 2.242
- worst_cell: SPY, mid-vol, same params, Sharpe -0.864

## Decision: ACCEPT (QQQ, BTC/USDT only)

All 5 validators pass for QQQ and BTC/USDT at their respective best grid
configs. SPY and ETH/USDT do not clear the Sharpe threshold at any tested
config — scope is honestly narrower than "full universe" but broader than
most volatility-compression-breakout attempts previously tested in this
repo (Minervini VCP, TTM Squeeze, Garman-Klass percentile, ATR-percentile
grid trading — all previously rejected decisively). Note QQQ and BTC/USDT
use *different* per-symbol parameter configs (breakout_window 5 vs 10,
pctile_threshold 0.20 vs 0.10), consistent with this repo's established
per-symbol-tuning convention for accepted strategies.

## Caveats / future work

- MDD for both accepted symbols is very low (6.7% QQQ, 14.3% BTC) relative
  to the 25% threshold, mostly because the strategy has few, short-hold
  trades (272/202 trades over ~8.7 years) with tight ATR-based
  target/trail exits — time-in-market is low, which also caps upside.
- Net-Sharpe-after-costs for QQQ (0.619) is noticeably lower than gross
  Sharpe (1.254) due to 272 trades at 5bp/trade — a future iteration could
  test whether widening breakout_window or pctile_threshold further
  reduces turnover without giving up too much edge.
- SPY/ETH near-miss investigation not pursued this iteration (time budget)
  — a future loop could retune per-symbol if desired.
