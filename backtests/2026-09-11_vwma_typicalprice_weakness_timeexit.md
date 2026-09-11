# 2026-09-11 VWMA Typical-Price Weakness Dip-Buy + Fixed Time-Exit (QQQ/SPY)

**Hypothesis:** Per QuantifiedStrategies.com's "Volume Weighted Average
Price (VWAP) Trading Strategy: Backtest and Evaluation"
(https://www.quantifiedstrategies.com/volume-weighted-average-price/,
visited 2026-09-11), the site's own "Strategy 3" SPY backtest ("When the
close of SPY crosses BELOW the N-day [volume-weighted] moving average, we
sell after N-days") showed positive average-gain-per-trade at every N
tested (5..200). This repo variant: entry when close crosses below a
`window`-day VWMA of the TYPICAL PRICE (H+L+C)/3, exit after a fixed
`hold_days` time-stop (no crossback condition), single-position-at-a-time.
Distinct from accepted VWMA dual-crossover (2026-09-04-060) and rejected
VWMA pullback-bounce (2026-09-08-070).

## Grid test (window in [10,25,50] x hold_days in [10,25,50], QQQ/SPY/BTC-ETH, 3 vol terciles, 2018-01-01..2026-09-01)

- total_cells: 108, passed_cells: 17, **pass_fraction: 0.157**
- by_asset_class: equity 17/54 passed, crypto 0/54 passed (decisive rejection on crypto)
- by_vol_regime: low 14/36, mid 3/36, high 0/36 (edge concentrated almost entirely in low-vol regime)
- best_cell: window=10, hold_days=25, SPY, low-vol, Sharpe=2.43
- worst_cell: window=50, hold_days=10, QQQ, low-vol, Sharpe=-0.75

## Single-config validation (window=10, hold_days=25 -- grid's best cell config, full sample)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample) | 0.866 | 0.913 | >= 1.0 | **FAIL both** |
| Max Drawdown | 0.293 | 0.322 | <= 0.25 | **FAIL both** |
| TC survival (10bps/trade, ~68-69 trades/8yr) | 0.817 | 0.851 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 1.0 | 1.0 | >= 0.75 | PASS |
| Parameter sensitivity (9-cell grid rel-std) | 0.218 | 0.319 | <= 0.5 | PASS |

## Decision: REJECTED

Full-sample Sharpe and max-drawdown both fail for both QQQ and SPY at the
grid's own best config. The grid's promising low-vol-tercile cells
(Sharpe up to 2.43) do not survive when blended across the full
multi-regime sample -- the strategy's edge is real but confined almost
entirely to low-vol regimes (14/36 low vs 3/36 mid vs 0/36 high pass),
consistent with a mean-reversion-on-weakness mechanic that gets run over
in high-vol/trending-down conditions (fixed time-stop holds through
adverse moves rather than cutting losses). A future iteration could revisit
with an explicit low-vol-regime gate (similar to 2026-09-03-001's BB
mean-reversion design) rather than trading the signal unconditionally.
