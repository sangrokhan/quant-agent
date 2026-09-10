# 2026-09-10 Weinstein Stage 2 Breakout + Vol-Regime Gate — Backtest Report

**Hypothesis (id 2026-09-10-128):** Direct fix attempt for this cron
trigger's near-miss 2026-09-10-127 (plain Weinstein Stage 2 breakout,
full-sample Sharpe failed 0.679/0.700 QQQ/SPY despite MDD/TC/walk-forward/
param-sensitivity passing). Adds an explicit low-volatility regime AND-gate
(20d realized vol <= trailing 252d median -- identical construction to the
accepted `2026-09-03_bb_meanrev_qqq_volregime.py`) on top of the unchanged
Stage 2 entry/exit mechanics, motivated by the prior grid's own
`by_vol_regime` breakdown (edge concentrated in the low-vol tercile,
best-cell Sharpe 2.81) and generically corroborated by
https://pyquantlab.medium.com/an-algorithmic-exploration-of-a-trend-following-strategy-with-regime-filter-and-dynamic-stops-70a7c6d41134
(visited this iteration: trend-following systems benefit from an explicit
volatility regime filter).

## Grid test summary (Step 6)

- Grid: `sma_window in [100,150] x breakout_window in [30,50,70] x
  max_hold_days in [40,60]`, symbols `{equity: [QQQ, SPY], crypto:
  [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3. 144 total cells.
- `pass_fraction`: 36/144 = 0.25 (up from 0.199 in the ungated version)
- `by_asset_class`: equity 36/72 (0.50, up from 0.398), crypto 0/72 (still
  decisive reject)
- `by_vol_regime`: low 24/48 (0.50), mid 0/48 (0.0, down from 0.097), high
  12/48 (0.25, up from 0.0 -- unexpected, the low-vol gate still lets some
  high-tercile *dates* through since the gate is evaluated at entry time not
  the vol-regime bucketing used for reporting)
- `best_cell`: sma_window=100/breakout_window=50/max_hold_days=60, SPY,
  low-vol regime, Sharpe 2.75 (essentially unchanged from the ungated
  version's 2.81 best cell)

## Single-config validation (Step 7) — best grid config, full sample

Config: `sma_window=100, breakout_window=50, max_hold_days=60` (vol-gate
params at defaults: vol_window=20, vol_lookback=252, vol_regime_ratio=1.0).

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** 0.565 | **FAIL** 0.796 |
| Max Drawdown (<=0.25) | pass 0.131 | pass 0.141 |
| TC survival (net Sharpe >=0.5) | pass 0.523 | pass 0.742 |
| Walk-forward (>=0.75 splits positive) | pass 1.00 (4/4, up from 3/4) | pass 1.00 (4/4, up from 3/4) |
| Param sensitivity (rel std <=0.5) | pass 0.151 | pass 0.219 |

## Decision: REJECTED

The vol-regime gate did NOT rescue full-sample Sharpe -- QQQ actually got
*worse* (0.565 vs 0.679 ungated) while SPY improved somewhat (0.796 vs
0.700) but still misses the 1.0 threshold. Walk-forward robustness did
improve to a clean 4/4 for both symbols (up from 3/4), and the grid's
overall equity pass_fraction rose from 0.398 to 0.50, but the primary
Sharpe validator remains the blocking failure. The gate restricts the
strategy to fewer, more selective trades (QQQ num_trades roughly unchanged
at 26 vs 22 prior -- entries aren't meaningfully rarer, they're just
differently timed), which doesn't concentrate enough of the return into the
low-vol high-Sharpe pockets to lift the full-sample statistic above 1.0.

This closes out the Weinstein Stage Analysis angle for this cron trigger:
two direct variants tested (plain Stage 2 breakout, vol-gated Stage 2
breakout), both rejected on the same Sharpe threshold with a consistent
~0.85-3x-below-threshold-in-low-vol-only pattern. A future loop could try
restricting the ENTIRE backtest window to only the low-vol tercile (rather
than gating individual entries) or pairing this with the CCI/Vortex-style
ADX trend-strength confirmation the PyQuantLab source also recommends.
