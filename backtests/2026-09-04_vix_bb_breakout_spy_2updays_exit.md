# Backtest Report: VIX Bollinger-Band Breakout → SPY, 2-3 Up-Day Exit

**Strategy file:** `strategies/2026-09-04_vix_bb_breakout_spy_2updays_exit.py`
**Hypothesis ID:** 2026-09-04-103
**Source:** https://www.quantifiedstrategies.com/using-vix-to-trade-spy-and-sp-500/

## Hypothesis

QuantifiedStrategies.com's VIX-SPY article frames VIX as a mean-reversion
indicator that moves almost perfectly inversely to SPY. Their concrete rule:
go long SPY when VIX closes above its own upper Bollinger Band (a spike in
the vol-of-vol), exit after N consecutive SPY up-days (N=2 primary variant).
Source backtested (2005-2012) multiple BB std widths, all producing positive
average per-trade returns (std=2.5: 1.44%/trade avg, 25 trades; std=1.0:
0.42%/trade avg, 135 trades).

This is the first strategy in this repo whose signal comes from a SEPARATE
cross-asset volatility proxy (VIX) rather than the traded asset's own price
series.

## Single-config validators (primary config: bb_std=2.5, exit_up_days=3, SPY, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.63 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.309 | ≤ 0.25 | **FAIL** |
| Transaction cost survival (10bps/trade, 42 trades) | net Sharpe 0.57 | ≥ 0.5 | PASS |
| Walk-forward (4 contiguous splits, manual — `vbt.utils.splitting` API unavailable in installed vectorbt version) | 3/4 splits positive Sharpe (0.75) | ≥ 0.75 | PASS |
| Parameter sensitivity (bb_std×exit_up_days grid, relative std) | 0.150 | ≤ 0.5 | PASS |

## Step 6 grid summary (bb_std∈{1.5,2.0,2.5} × exit_up_days∈{2,3}, SPY+QQQ, vol_regime_splits=3)

- Total cells: 36, passed: 17, **pass_fraction = 0.472**
- By vol regime: low 12/12 (100%), mid 4/12 (33%), high 1/12 (8%)
- Best cell: bb_std=2.5, exit_up_days=3, SPY, low-vol regime, Sharpe 2.85
- Worst cell: bb_std=2.5, exit_up_days=2, SPY, high-vol regime, Sharpe 0.14
- Equity-only (VIX has no crypto/BTC analog — genuinely single-asset-class strategy, same epistemic status as the Bitcoin halving-cycle calendar strategy 2026-09-04-096, which was crypto-only).

## Decision: REJECTED

Despite a strong grid pass_fraction (47%) concentrated almost entirely in
low-realized-vol regimes, the full-sample Sharpe (0.63) and max drawdown
(30.9%) both fail this repo's standard thresholds on the best-performing
grid config. The strategy's edge appears real but narrow: it captures VIX
spikes cleanly in calm markets but the SPY 2-3-day-up-day exit doesn't
control drawdown during genuine high-vol regime stress (only 1/12 high-vol
cells passed) — consistent with the source's own framing of this as a
short-term mean-reversion bounce play, not a full-cycle risk-managed
system. A future iteration could revisit by adding a max-drawdown-aware
stop or restricting entries to only fire when NOT already in a high-vol
regime (avoiding entering right as a crash regime begins, rather than
after a single-day spike).
