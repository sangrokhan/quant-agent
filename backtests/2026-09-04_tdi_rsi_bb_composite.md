# Traders Dynamic Index (TDI) RSI+Bollinger Composite — Backtest Report (2026-09-04)

## Hypothesis
Traders Dynamic Index (TDI, Dean Malone): an all-in-one RSI + Bollinger
Band indicator -- 13-day RSI, fast (2-day SMA) and slow (7-day SMA)
moving averages of the RSI, and 34-day Bollinger Bands (1.6185 std) of
the RSI itself (upper/middle/lower). Source's explicit free rules: BUY
when fast RSI-MA > mid band AND slow RSI-MA > mid band AND fast RSI-MA <
upper band; SELL when (fast+slow RSI-MA both > 70) OR (fast+slow RSI-MA
both < mid band). Source's own SPY backtest found lower absolute CAGR
than buy-and-hold but much better risk-adjusted return (MDD -27% vs
-55%, only ~29% time in market).

Source: https://www.quantifiedstrategies.com/traders-dynamic-index/
(web_search failed for the original Vortex+RSI query -- DDGS/RequestError
-- fell back to browser_exec Google search, whose SERP surfaced this TDI
article as a top result with explicit free rules; used that instead of
Vortex+RSI since Vortex is already tested standalone in this repo).

## Grid summary (Step 6)
`param_grid={fast_ma:[2,3], max_hold_days:[15,20,30]}` (rsi_period=13,
slow_ma=7, bb_window=34, bb_std=1.6185, overbought=70 fixed), symbols
`{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=72, passed_cells=12, **pass_fraction=0.167**
- by_asset_class: equity 12/36, crypto **0/36**
- by_vol_regime: low **12/24**, mid 0/24, high 0/24 (entirely low-vol-concentrated)
- best_cell: fast_ma=2, max_hold_days=15, QQQ, low-vol, Sharpe=2.15
- worst_cell: fast_ma=2, max_hold_days=20, SPY, mid-vol, Sharpe=-0.24

## Single-config validation (Step 7)
Config: fast_ma=2, max_hold_days=15 (grid-best cell config). Full sample
2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.714 (**fail**) | 0.715 (**fail**) |
| Max drawdown (<=0.25) | 0.296 (**fail**) | 0.232 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 0.515 (pass) | 0.487 (**fail**, near-miss) |
| Walk-forward, manual 4-split fallback (>=0.75 pass frac) | 0.75, 3/4 splits positive (pass) | 0.75, 3/4 splits positive (pass) |
| Parameter sensitivity (fast_ma x max_hold_days sweep, rel std <=0.5) | 0.048 (pass) | 0.080 (pass) |
| num_trades | 133 | 128 |

Same manual 4-equal-slice walk-forward fallback as prior iterations
(vectorbt `RangeSplitter` still broken in this install).

## Decision (Step 8)
**Reject for both QQQ and SPY** — full-sample Sharpe fails decisively on
both (0.714 and 0.715, both well under the 1.0 threshold) despite the
grid-best-cell figure (2.15 on QQQ low-vol) looking attractive -- the same
narrow-low-vol-tercile-overstates-full-sample-edge pattern flagged
repeatedly in this log (e.g. 2026-09-04-109 PPO, 2026-09-04-114 Double 7s).
QQQ additionally breaches the max-drawdown threshold (0.296); SPY
near-misses TC-survival (0.487<0.5).
**Reject for crypto** — 0/36 grid cells pass.

Nothing accepted this iteration. Consistent with the source's own finding
that TDI trades relatively infrequently (~29% time in market on their SPY
test) and underperforms buy-and-hold on absolute terms -- our full-sample
Sharpe result corroborates that this composite RSI+BB rule set is not by
itself a strong standalone edge at the thresholds this repo uses.
