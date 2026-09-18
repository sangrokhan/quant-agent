# 2026-09-18-068: Gann Fan 1x1-Line Trend Filter with Angle-Touch Bounce

## Hypothesis

Per QuantifiedStrategies.com's Gann Fan Trading Strategy article
(https://www.quantifiedstrategies.com/gann-fan-trading-strategy/), the
source discloses: (1) identify a swing pivot as the fan's origin, (2) draw
the "1x1 line" at 45 degrees from that pivot, (3) "price above 1x1 line ->
buy signal at Gann-angle intersections" (trend-following rule). Since
Gann's original fixed 1-price-unit-per-1-time-unit convention is
scale-dependent, we scaled the 1x1 slope by the instrument's own ATR at the
pivot bar (standard practical adaptation), giving a volatility-proportional
decaying reference line from each new swing-high pivot. Long entry when
close crosses back above this decaying 1x1 line (confirmed by close above
the pivot's own low); exit on close crossing back below the line or a
time-stop.

Source: https://www.quantifiedstrategies.com/gann-fan-trading-strategy/

First Gann Fan / Gann angle strategy in this repo (existing Gann HiLo
Activator entries are Krausz's unrelated separate indicator).

## Step 6 grid summary

`param_grid={pivot_lookback: [20,40,60], atr_window: [14,21], max_hold_days:
[15,20,25]}`, `symbols={equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, 2018-01-01..2026-09-01.

- total_cells=216, passed_cells=27, pass_fraction=0.125
- by_asset_class: equity 25/108, crypto 2/108 (decisively equity-only in
  the grid's per-vol-regime cells, though full-sample crypto Sharpe was
  higher on average across param combos due to averaging effects -- see
  single-config validation below for why this is misleading)
- by_vol_regime: low 25/72, mid 2/72, high 0/72
- best_cell (single vol-regime slice): ETH/USDT mid-vol, pivot_lookback=40,
  atr_window=21, max_hold_days=25, Sharpe 2.39
- worst_cell: QQQ high-vol, pivot_lookback=60, atr_window=21,
  max_hold_days=15, Sharpe -1.71
- Best average-across-vol-regimes config: ETH/USDT (pivot_lookback=40,
  atr_window=14, max_hold_days=25) avg Sharpe 0.802, pass 1/3 vol regimes.

## Single-config validation (ETH/USDT, pivot_lookback=40, atr_window=14,
max_hold_days=25, 2018-01-01..2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.214 | 1.0 | **fail** |
| Max drawdown | 0.438 | 0.25 | **fail** |
| Net Sharpe after costs (10bps/trade, 5427 trades) | -0.016 | 0.5 | **fail** |
| Parameter sensitivity (relative std, 18-combo ETH grid) | 0.224 | 0.5 | pass |

The single-vol-regime "mid" cell's strong Sharpe (2.39) does not survive
full-sample averaging -- the strategy churns heavily (5427 trades over the
sample on ETH/USDT hourly bars via `data/loaders.py::load_crypto`'s default
1h interval) and the full-sample Sharpe/MDD/cost-survival collapse
decisively. This is consistent with a fragile, overfit-to-one-regime result
rather than a genuine edge.

## Decision

**Rejected.** Full-sample Sharpe (0.214), max drawdown (0.438), and
transaction-cost survival (net Sharpe -0.016 after 5427 trades) all fail
decisively despite a promising isolated grid cell. The single-config
validation on the best average-Sharpe config exposes that the grid's
strong per-vol-regime cells do not generalize -- likely an artifact of
averaging a high-trade-frequency, volatility-scaled reference line that is
too reactive (re-anchoring on every new swing high) to survive realistic
transaction costs. A future iteration wanting to revisit Gann angles should
either (a) use a much longer/rarer pivot re-anchor cadence to cut trade
frequency, or (b) test on daily-only intervals explicitly rather than
relying on `load_crypto`'s default 1h bars, which produced an
unrepresentatively high trade count for a daily-signal design.
