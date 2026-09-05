# Qstick (EMA variant) signal-line crossover — backtest report

**Strategy file:** `strategies/2026-09-06_qstick_signal_crossover.py`
**Hypothesis id:** 2026-09-06-105

## Hypothesis

Qstick indicator (Tushar Chande): QSI = EMA(close-open, qstick_window);
Signal = EMA(QSI, signal_window). Long entry when QSI crosses above Signal;
exit when Signal crosses back above QSI, or a max_hold_days time-stop. Per
https://www.quantifiedstrategies.com/qstick-indicator-strategy/ ("We buy
when the Qstick indicator crosses above the signal line. We sell and move
to cash when the signal line crosses under the Qstick indicator"; source's
own SPY backtest used 100-day EMA of (close-open) / 50-day signal EMA,
CAGR 6.98%, MDD 35.29%, no explicit stop-loss).

Distinct from already-rejected Qstick variant 2026-09-04-136 (SMA-based,
single-indicator-vs-own-SMA + sign-confirmation filter) via (1) EMA instead
of SMA per source's own finding that EMA slightly outperforms, (2) a
genuine two-line signal-line crossover (source's exact rule) rather than an
indicator-vs-itself-plus-sign-filter construction, (3) no positive/negative
sign gate.

## Grid summary (Step 6)

`qstick_window` in {50,100,150} x `signal_window` in {20,50} x
`max_hold_days` in {20,40}, symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT
(crypto), vol_regime_splits=3: 144 cells total, 32 passed
(pass_fraction=0.222).

- by_asset_class: equity 32/72 (44%), crypto 0/72 (0%, decisively rejected)
- by_vol_regime: low 24/48 (50%), mid 8/48 (17%), high 0/48 (0%) — edge
  concentrated almost entirely in low-vol equity slices, same pattern as
  the prior SMA-based Qstick rejection.
- best_cell: qstick_window=50, signal_window=50, max_hold_days=40, SPY,
  low-vol, Sharpe=3.03
- worst_cell: qstick_window=100, signal_window=50, max_hold_days=40, SPY,
  mid-vol, Sharpe=-1.03

## Full-sample (non-vol-sliced) Sharpe/MDD sweep, QQQ and SPY

All 24 param combos (both symbols) computed full-period Sharpe and MDD;
**every single combo failed the Sharpe>=1.0 threshold** on both QQQ and SPY
full-sample:

- QQQ best: qstick_window=150, signal_window=20, max_hold_days=40 ->
  Sharpe=0.671, MDD=0.299
- SPY best: qstick_window=50, signal_window=50, max_hold_days=40 ->
  Sharpe=0.340, MDD=0.219

## Decision: REJECT

Grid-cell Sharpe values that look attractive (up to 3.03) only hold within
a narrow low-vol equity tercile; the full-sample Sharpe (the metric that
matters for a deployable signal) fails the 1.0 threshold across every
tested parameter combination on both equity symbols, and crypto fails
decisively (0/72 grid cells). No further validator suite run (walk-forward,
transaction-cost survival, parameter sensitivity) since Sharpe already
fails outright on the primary full-sample metric — consistent with
`suggested_workload=max` but a clear-cut early-reject case per Step 7
guidance (run whichever subset is relevant; further steps would not change
the reject/accept decision here).
