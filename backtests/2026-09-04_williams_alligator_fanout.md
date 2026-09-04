# Williams Alligator Fan-Out Crossover — Backtest Report (2026-09-04)

## Hypothesis
Williams Alligator (Bill Williams, 1995): three Fibonacci-period smoothed
moving averages (SMMA) on median price — Jaw SMMA(13) shifted forward 8
bars, Teeth SMMA(8) shifted forward 5 bars, Lips SMMA(5) shifted forward 3
bars. When the lines are tangled/close ("sleeping"), the market is
range-bound and signals are unreliable; when they fan apart in order
("awake"), a genuine trend is present. Tested crossover rule: go long when
Lips crosses above BOTH Teeth and Jaw (alligator waking up bullishly); exit
when Lips crosses back below either line (mouth closing), or after
`max_hold_days` as a time-stop safety net (source article gives no explicit
stop-loss rule of its own).

Source: https://howtotrade.com/indicators/alligator-indicator/

## Grid summary (Step 6)
`param_grid={jaw_period:[13,21], max_hold_days:[15,25]}` (teeth/lips periods
and all shift amounts held at Fibonacci defaults 8/5/5/3), symbols
`{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=48, passed_cells=12, **pass_fraction=0.25**
- by_asset_class: equity 12/24, crypto **0/24**
- by_vol_regime: low 8/16, mid 4/16, high **0/16**
- best_cell: jaw_period=13, max_hold_days=15, QQQ, low-vol, Sharpe=2.92
- worst_cell: jaw_period=13, max_hold_days=15, SPY, high-vol, Sharpe=-0.38

Pattern consistent with most prior trend-following strategies in this repo:
works only in low/mid-vol equity regimes, decisively fails on crypto and
high-vol regimes.

## Single-config validation (Step 7)
Config: jaw_period=13/shift=8, teeth_period=8/shift=5, lips_period=5/shift=3,
max_hold_days=15. Full sample 2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **1.339 (pass)** | 0.672 (fail) |
| Max drawdown (<=0.25) | 0.151 (pass) | 0.168 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 1.187 (pass) | 0.495 (fail) |
| Walk-forward, 4 splits (>=0.75 pass frac) | 1.0 (pass) | 1.0 (pass) |
| Parameter sensitivity (jaw_period in {8,13,21,34}, rel std <=0.5) | 0.135 (pass) | 0.096 (pass) |
| num_trades | 102 | 103 |

## Decision (Step 8)
**Accept for QQQ** (jaw_period=13, max_hold_days=15) — all 5 validators pass.
**Reject for SPY** — Sharpe (0.672) and TC-survival net Sharpe (0.495) both
miss threshold at the same config; walk-forward and param-sensitivity pass,
but the headline Sharpe/cost miss is decisive.
**Reject for crypto (BTC/USDT, ETH/USDT)** — 0/24 grid cells pass; the
fan-out momentum-continuation logic does not transfer to 24/7 crypto
markets, consistent with most other trend-following strategies tested in
this repo (2026-09-04-053 SuperTrend, 2026-09-04-054 Donchian, etc.).
