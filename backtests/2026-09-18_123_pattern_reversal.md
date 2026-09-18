# Backtest Report: 123 Pattern Bullish Reversal (SPY, max_hold_days=30)

**Date:** 2026-09-18
**Status:** REJECTED

## Hypothesis

Source: https://www.quantifiedstrategies.com/123-pattern-reversal-strategy/

A bullish 123 reversal is confirmed by a 4-bar low/high structural break
(source's own disclosed mechanical rule, backtested there on GLD):
- Today's low < yesterday's low
- Yesterday's low < the low from 3 days ago
- The low from 2 days ago < the low from 3 days ago
- The high from 2 days ago < the high from 3 days ago

Exit: fixed N-day time exit (source reported 20-day exit best profit
factor 2.22 on GLD). Adapted here long-only, generalized to any OHLC
price_df, with `max_hold_days` tunable.

## Step 6 grid summary (`grid_result_123_pattern_reversal.json`)

- param_grid: `max_hold_days` in [10, 20, 30]
- symbols: equity (QQQ, SPY), crypto (BTC/USDT, ETH/USDT)
- vol_regime_splits: 3
- **pass_fraction: 0.222 (8/36 cells)**
- by_asset_class: equity 8/18 passed, crypto 0/18 passed (decisive crypto reject)
- by_vol_regime: low 6/12, mid 2/12, high 0/12 (regime-dependent, fails in high-vol)
- best_cell: SPY, max_hold_days=30, low-vol regime, Sharpe 2.08
- worst_cell: BTC/USDT, max_hold_days=10, low-vol regime, Sharpe -0.22

## Step 7 single-config validation (SPY, max_hold_days=30, full sample 2015-09-01 to 2026-09-01)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.792 | >= 1.0 |
| Max drawdown | **FAIL** | 0.307 | <= 0.25 |
| TC survival (10bps/trade, 70 trades) | pass | net Sharpe 0.739 | >= 0.5 |
| Walk-forward (4 splits) | pass | 1.0 pass fraction | >= 0.75 |
| Parameter sensitivity (max_hold_days 10/20/30) | pass | rel_std 0.291 | <= 0.5 |

## Decision: REJECT

Full-sample Sharpe (0.79) and max drawdown (0.31) both fail thresholds,
even though the grid's isolated low-volatility tercile showed a strong
Sharpe (~2.08 on SPY, ~1.86 on QQQ). This is a regime-dependent pattern:
it performs well in calm/low-vol markets but degrades in mid/high-vol
regimes, dragging down the full-sample Sharpe and inflating full-sample
drawdown. Crypto is decisively rejected across the whole grid (0/18).

Left `strategies/2026-09-18_123_pattern_reversal.py` in place as a record
of a rejected attempt -- a future iteration could revisit this with an
explicit low-vol regime gate (following this repo's established
regime-gating pattern, e.g. 2026-09-03_bb_meanrev_qqq_volregime.py) as a
"rescue" candidate, since the underlying low-vol-tercile Sharpe is
promising.
