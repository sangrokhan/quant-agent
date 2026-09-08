# Backtest report: Williams %R + Bollinger middle-band ATR reversal (REJECTED)

**Strategy file:** `strategies/2026-09-09_willr_bb_atr_reversal.py`

## Hypothesis

Per Tradie Capital's DEFI backtest snapshot
(https://www.tradiecapital.com/blog/backtests/defi-williams-bbands-reversal-strategy-backtest),
a long-only reversal combining Williams %R(14) crossing back above -80
(recovering from oversold) with close still below/at the 20-day Bollinger
middle band, exited at mean-reversion to the middle band / WILLR > -20 /
ATR-scaled stop-target / max hold, might generalize beyond the source's
single thinly-traded DEFI ticker (16 trades) to QQQ/SPY/BTC/ETH.

Source reported (DEFI, 16 trades, 2023-07-03..2026-06-29): 50% win rate,
1.36 profit factor, +2.71% return, 4.78% max drawdown.

## Step 6 grid summary (run_strategy_grid)

- param_grid: `willr_entry_thresh=[-85,-80,-75]` x `stop_atr_mult=[2.0,2.75,3.5]`
- symbols: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- vol_regime_splits=3 (low/mid/high terciles)
- **total_cells=108, passed_cells=0, pass_fraction=0.0**
- by_asset_class: equity 0/54, crypto 0/54
- by_vol_regime: low 0/36, mid 0/36, high 0/36
- best_cell: willr_entry_thresh=-75, stop_atr_mult=3.5, BTC/USDT low-vol, Sharpe=0.383 (still below 1.0 threshold)
- worst_cell: willr_entry_thresh=-75, stop_atr_mult=2.0, SPY low-vol, Sharpe=-1.363

Zero out of 108 cells passed the Sharpe>=1.0 threshold in any asset class or
volatility regime — this is a decisive, uniform failure, not a narrow-scope
finding.

## Single-config validation (best grid cell: willr_entry_thresh=-75, stop_atr_mult=3.5)

| Symbol | Sharpe | MDD |
|---|---|---|
| QQQ | -0.440 (fail, thresh 1.0) | 0.488 (fail, thresh 0.25) |
| SPY | -0.157 (fail, thresh 1.0) | 0.274 (fail, thresh 0.25) |

Both Sharpe and max-drawdown validators fail decisively on both equity
symbols at full sample. Given the grid's uniform 0% pass fraction, walk-forward
and parameter-sensitivity checks were skipped (workload=max but result
already unambiguous — no config in the 108-cell grid cleared the Sharpe bar).

## Outcome: REJECTED

Decisive rejection: 0/108 grid cells passed, negative full-sample Sharpe on
both equity symbols, MDD nearly double the 25% threshold on QQQ. The
source's reported edge (50% win rate / 1.36 PF on 16 DEFI trades) does not
generalize to QQQ/SPY/BTC/ETH with this rule translation — likely because
DEFI's crypto-native volatility/trend character (and possibly a favorable
lucky sample of 16 trades) doesn't transfer, and the WILLR-recovery +
below-middle-band entry may simply be too permissive (fires often, catches
continuing downtrends rather than genuine reversals) without the source's
undisclosed additional trend/momentum filter ("Entries required the trend
and momentum filters to agree" — the source's text hints at more filters
than the explicit rule block discloses).
