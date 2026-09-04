# Double 7s (Larry Connors) N-Day Low/High Mean-Reversion — Backtest Report (2026-09-04)

## Hypothesis
Larry Connors' "Double 7s": in a long-term uptrend (close > SMA(trend_window),
default 200), a fresh short-term N-day low (default N=7 for both entry and
exit lookback, hence "double") marks a tactical dip-buy; exit on a fresh
N-day high. A max_hold_days safety time-stop was added since the source's
own worked variants show the exit sometimes takes a while to fire.

Source: https://www.quantifiedstrategies.com/buy-the-dip-strategy/ (search
results for the canonical Double-7 article 404'd; this page explicitly
describes the original Larry Connors Double Seven rule as its baseline
before presenting its own modified "buy the dip" variant).

## Grid summary (Step 6)
`param_grid={entry_window:[5,7,10], exit_window:[5,7]}` (trend_window=200,
max_hold_days=15 fixed), symbols `{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01..2026-09-01.

- total_cells=72, passed_cells=12, **pass_fraction=0.167**
- by_asset_class: equity 12/36, crypto **0/36**
- by_vol_regime: low **12/24**, mid 0/24, high 0/24 (concentrated entirely
  in low-vol slices — even narrower than most prior strategies)
- best_cell: entry_window=7, exit_window=7 (the classic Double-7 config),
  SPY, low-vol, Sharpe=2.85
- worst_cell: entry_window=10, exit_window=7, QQQ, mid-vol, Sharpe=-0.44

## Single-config validation (Step 7)
Config: trend_window=200, entry_window=7, exit_window=7 (classic Double-7),
max_hold_days=15. Full sample 2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.802 (fail) | 0.591 (fail) |
| Max drawdown (<=0.25) | 0.156 (pass) | 0.188 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 0.689 (pass) | 0.452 (fail) |
| Walk-forward, 4 splits (>=0.75 pass frac) | 0.75 (pass) | 0.5 (fail) |
| Parameter sensitivity (entry_window in {5,7,10}, rel std <=0.5) | 0.318 (pass) | 0.095 (pass) |
| num_trades | 71 | 67 |

## Decision (Step 8)
**Reject for both QQQ and SPY** — full-sample Sharpe fails on both symbols
(0.80 and 0.59, both < 1.0 threshold) despite the grid's best-cell figure
(2.85 on SPY low-vol) looking attractive; this is the same "grid-best-cell
Sharpe on a narrow low-vol tercile substantially overstates the strategy's
real full-sample edge" pattern already flagged in this repo's notes for
2026-09-04-109 (PPO). SPY additionally fails TC-survival and walk-forward
(only 2/4 quarters positive).
**Reject for crypto** — 0/36 grid cells pass; a dip-buy rule keyed to
7-day-low/high closes on an uptrend filter does not transfer to crypto.

No accepted config from this iteration.
