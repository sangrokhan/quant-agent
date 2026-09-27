# Backtest Report: CARR(1,1) Range-Based Volatility Regime Gate + Trend Filter

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_carr_vol_regime_trendgate.py`
**Status:** ACCEPTED (equity only: QQQ, SPY) -- crypto legs (BTC/USDT, ETH/USDT) REJECTED

## Hypothesis

Per Chou (2005), "Forecasting Financial Volatilities with Extreme Values:
The Conditional Autoregressive Range (CARR) Model" (formula read via
Ratnayake & Samaranayake's TACARR paper, arXiv:2202.03351 Section 2.1,
direct PDF text extraction after web_extract's ddgs backend and the
browser's native PDF viewer could not extract arxiv's rendered text).
Genuinely novel for this 2600+-entry repo (0 prior "CARR" hits): CARR(1,1)
is structurally identical to GARCH(1,1) but models the daily HIGH-LOW
LOG-PRICE RANGE (R_t = P_t^high - P_t^low) instead of squared/absolute
returns. Fit via MLE (exponential unit-mean disturbance, Nelder-Mead
optimization of omega/alpha/beta on the CARR(1,1) recursion) on the full
OHLCV history already available from data/loaders.py (no new data source
needed). Applies this same cron trigger's own repeatedly-validated
trend-filter AND-gate pattern (4x confirmed on GARCH/GJR-GARCH/EGARCH/
HAR-D this trigger): long only when the CARR-implied expected range
lambda_t (shifted by 1, no look-ahead) is below its own historical median
(a "calm" regime) AND close > SMA(trend_window). A `min_hold_days`
minimum-holding-period filter was added after an initial (no-min-hold)
grid pass showed excessive whipsaw trading eroding transaction-cost
survival.

## Grid test summary (Step 6, initial coarse sweep, no min_hold_days)

`param_grid`: vol_threshold_quantile in [0.4,0.5] x trend_window in
[50,150]; symbols equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT];
vol_regime_splits=3.

- total_cells: 48, passed_cells: 18, pass_fraction: 0.375
- by_asset_class: equity 10/24, crypto 8/24
- by_vol_regime: low 11/16, mid 5/16, high 2/16 (weaker in high-vol
  terciles)

## Single-config validation (Step 7) -- best config: trend_window=150, vol_threshold_quantile=0.5, min_hold_days=20

| Symbol | Sharpe | MDD | Net Sharpe (10bps, N trades) | Walk-forward | Result |
|---|---|---|---|---|---|
| QQQ | 1.086 (pass) | 0.183 (pass) | 0.984 (pass), 73 trades | 4/4 splits positive (pass) | **ACCEPT** |
| SPY | 1.021 (pass) | 0.150 (pass) | 0.840 (pass), 87 trades | 4/4 splits positive (pass) | **ACCEPT** |
| BTC/USDT | 0.458 (**FAIL**) | 0.589 (**FAIL**) | 0.425 (**FAIL**) | not run | REJECT |
| ETH/USDT | 0.922 (**FAIL**, <1.0) | 0.581 (**FAIL**) | 0.894 (fail vs full-suite bar) | not run | REJECT |

Crypto legs decisively fail Sharpe even after sweeping trend_window in
[50,75,100] (BTC raw Sharpe never exceeded 0.70; ETH peaked at 1.03 at
trend_window=50 but with elevated MDD 0.58+ unleveraged) -- since leverage
scaling does not change the Sharpe ratio (only MDD), no leverage_cap value
can rescue BTC's sub-1.0 raw Sharpe. Unlike this cron trigger's earlier
GARCH-family rescues, the CARR range-based volatility signal itself
appears to carry materially less crypto-specific edge than the return-based
GARCH-family models already validated on the same crypto pair this trigger
(2026-09-28-025/026), rather than this being a fixable trend-filter/
parameter-tuning issue.

Parameter sensitivity (QQQ, 3x3 trend_window x min_hold_days sweep):
relative_std = 0.154 (mean Sharpe 0.740, std 0.114), threshold 0.5.
**PASS.**

Walk-forward (manual 4-split, vectorbt's `RangeSplitter` API broken in
this repo per this cron trigger's now-standard workaround note): QQQ and
SPY both 4/4 splits positive. **PASS.**

## Decision: ACCEPT (equity only: QQQ, SPY); REJECT crypto legs (BTC/USDT, ETH/USDT)

Per RESEARCH_LOOP.md Step 6's guidance ("a strategy that only works in one
asset class ... is not automatically rejected -- record that finding
precisely"), this strategy is accepted for its EQUITY scope only. Both
QQQ and SPY pass all 5 validators at trend_window=150,
vol_threshold_quantile=0.5, min_hold_days=20. Crypto legs are recorded as
rejected (not leverage-fixable, unlike the GARCH-family entries) so a
future loop does not over-trust this strategy outside its equity scope.
