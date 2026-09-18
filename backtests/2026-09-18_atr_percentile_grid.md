# ATR-Percentile-Gated Grid Trading (2026-09-18)

## Hypothesis

QuantifiedStrategies.com's "Adaptive Grid Trading Strategy" activates a
mean-reversion grid only during HIGH relative-volatility regimes (ATR
Percentile -- rolling rank of current ATR within its own 100-200 bar
history -- >= 70-80th percentile) and deactivates (unwinds) during
low-vol regimes (<= 25-30th percentile), with ATR-scaled grid spacing so
identical thresholds work across assets of very different absolute
volatility without per-asset retuning.

Adapted to this repo's long/flat position-series interface (a literal
multi-order grid isn't a {0,1} position series): long entry when close
drops `grid_spacing_atr_mult` x ATR(14) below its own rolling
`grid_ref_window`-bar mean, but ONLY while ATR Percentile >=
`activate_pctile`; exit on reverting to the rolling mean, regime
deactivation (ATR Percentile <= `deactivate_pctile`), or a max-hold
time-stop.

Source: https://www.quantifiedstrategies.com/adaptive-grid-trading-strategy/
(fully disclosed formula and thresholds; fetched via browser_exec --
web_search DDGS backend failing this cron trigger throughout). First
ATR-Percentile-gated mean-reversion strategy in this repo.

## Grid test

`activate_pctile in {70,80} x grid_spacing_atr_mult in {1.0,1.5,2.0}`,
equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2018-01-01..2026-09-01:

- total_cells=72, passed_cells=1, **pass_fraction=0.014** -- essentially
  a decisive rejection; only a single grid cell (BTC/USDT mid-vol tercile,
  activate_pctile=70/grid_spacing_atr_mult=1.5, Sharpe 1.009) clears the
  bar, and that's within one narrow vol tercile, not full-sample.
- by_asset_class: equity 0/36, crypto 1/36.
- by_vol_regime: low 0/24, mid 1/24, high 0/24.
- worst_cell: SPY low-vol, Sharpe -1.033.

## Single-config validation (activate_pctile=70, grid_spacing_atr_mult=1.5)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe, 10bps) | Trades |
|---|---|---|---|---|
| QQQ | 0.137 (fail) | 0.284 (fail) | 0.110 (fail) | 28 |
| SPY | 0.095 (fail) | 0.344 (fail) | 0.063 (fail) | 29 |
| BTC/USDT | -0.009 (fail) | 0.737 (fail) | -0.049 (fail) | 723 |
| ETH/USDT | 0.008 (fail) | 0.868 (fail) | -0.029 (fail) | 737 |

Crypto's very high trade count (723/737) reflects `load_crypto`'s default
1h bar interval combined with a 200-bar ATR-percentile lookback that's
far too short at hourly resolution -- the regime gate flickers open/closed
constantly, producing near-continuous whipsaw entries. Even discounting
that granularity mismatch, the underlying full-sample Sharpe is
essentially zero for both crypto symbols.

## Verdict: REJECTED (decisive, all symbols, near-zero grid pass fraction)

Adapting a genuinely multi-order/multi-price-level grid-trading concept
into a single-position long/flat signal loses most of the edge the
original grid mechanism relies on (capturing many small round-trips at
different price levels simultaneously, not just one entry/exit per regime
window). This adaptation choice is likely the primary reason for the
weak full-sample performance, not necessarily a flaw in the underlying
ATR-percentile volatility-normalization idea itself -- a genuine multi-
level grid backtest would require a different execution/accounting
framework than this repo's single-position vectorbt-based validators
support, so this is filed as an architecture-mismatch rejection rather
than a pure edge-doesn't-exist rejection.
