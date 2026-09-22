# 2026-09-22 — Al Brooks Two-Leg Pullback Re-entry

**Hypothesis**: Source: https://algobars.com/strategy-templates/al-brooks/brooks-2leg-pullback/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). In a confirmed uptrend, pullbacks commonly form TWO
sequential down-legs; the second leg's completion (reaching or slightly
overshooting EMA(20)) offers the highest-probability re-entry, confirmed
by a bullish signal bar. First Two-Leg Pullback strategy in this repo (0
prior KB hits).

**Strategy file**: `strategies/2026-09-22_brooks_two_leg_pullback.py`

**Grid test** (`run_grid_brooks_two_leg_pullback.py`): param_grid =
`{trend_window: [30, 50, 80], ema_proximity_pct: [0.02, 0.04]}`, symbols =
equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), vol_regime_splits=3.
- total_cells=72, passed_cells=6, pass_fraction=0.083
- by_asset_class: equity 6/36, crypto 0/36
- by_vol_regime: low 0/24, **mid 6/24**, high 0/24
- best_cell: QQQ trend_window=30/ema_proximity_pct=0.02, mid-vol, Sharpe 1.52

**Single-config validators** (full-sample 2019-2026, QQQ,
`trend_window=30, ema_proximity_pct=0.02`):

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 0.729 | ≥1.0 | FAIL |
| Max drawdown | 0.013 | ≤0.25 | pass |
| TX-cost survival | 0.703 | ≥0.5 | pass |
| Trade count | **2** | -- | -- |

**Decision**: REJECTED. Only 2 trades over the full 2019-2026 sample --
far too sparse a sample to draw any statistical conclusion, and the grid's
mid-vol-tercile-only "pass" (6/72 cells) is consistent with the same
small-sample/single-regime artifact pattern seen repeatedly this cron
trigger. The two-sequential-swing-low structural requirement (leg 1 down,
partial bounce, leg 2 down to near EMA20, all within an active uptrend) is
simply too rare a conjunction on daily bars to produce a statistically
meaningful signal. Crypto fails completely (0/36 grid cells).
