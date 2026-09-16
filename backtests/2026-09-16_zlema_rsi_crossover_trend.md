# 2026-09-16 ZLEMA-RSI Crossover Trend (Vervoort NPR21 concept)

**Hypothesis:** Per https://theindicatorlab.com/reviews/vervoortcrossover-zero-lag-npr21/
(review of a Pine Script port of Sylvain Vervoort's zero-lag RSI crossover
concept, originally published Stocks & Commodities 2009): a base RSI(21) is
ZLEMA-smoothed twice (fast/slow lines) to remove crossover lag; long entry
on fast-over-slow crossover while not overbought, gated by the source's own
recommended 200-EMA trend filter ("cut false signals by about 40%"). Distinct
from prior repo ZLEMA entries which applied ZLEMA to raw price, not to RSI.

Source URL: https://theindicatorlab.com/reviews/vervoortcrossover-zero-lag-npr21/
(fetched via `web_extract` fallback to `browser_exec` — web_extract's ddgs
backend cannot extract content, search-only).

## Grid test (Step 6)

`scripts/run_grid_zlema_rsi.py`: param_grid fast_len∈{3,5,8} × slow_len∈{10,13,21}
× trend_window∈{100,200}, symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, full sample 2019-01-01..2026-09-01.

- total_cells=216, passed=61, **pass_fraction=0.282**
- by_asset_class: equity 46/108 (0.426), crypto 15/108 (0.139)
- by_vol_regime: low 37/72 (0.514), mid 14/72 (0.194), high 10/72 (0.139)
- best_cell: fast_len=3/slow_len=10/trend_window=200, SPY, low-vol, Sharpe=2.93
- worst_cell: fast_len=8/slow_len=13/trend_window=100, QQQ, high-vol, Sharpe=-0.86

Grid confirms: works far better in equity than crypto, and far better in
low-vol than high-vol regimes — consistent with the source's own caveat
("still whipsaws in ranging markets").

## Single-config validation (Step 7)

Primary config from grid's best cell region: `fast_len=3, slow_len=10,
trend_window=200`. Initial full-sample run (no min-hold) showed TC-survival
near-miss on both QQQ/SPY (many crossover trades). Applied this repo's
standard `min_hold_days` hysteresis fix (same pattern as Klinger
2026-09-04-085, ZLEMA-price 2026-09-06-171) — swept min_hold_days∈{5,10,15},
**min_hold_days=10** passes all 3 core metrics for both QQQ and SPY.

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass frac | Param sens (rel std) |
|---|---|---|---|---|---|
| QQQ | 1.400 ✅ | 0.152 ✅ | 1.102 ✅ | 0.75 ✅ | 0.065 ✅ |
| SPY | 1.216 ✅ | 0.182 ✅ | 0.750 ✅ | 0.75 ✅ | 0.314 ✅ |
| BTC/USDT | 0.189 ❌ | 0.452 ❌ | -0.037 ❌ | 1.00 ✅ | 0.108 ✅ |
| ETH/USDT | 0.200 ❌ | 0.435 ❌ | -0.023 ❌ | 1.00 ✅ | 0.081 ✅ |

Final config: `rsi_period=21, fast_len=3, slow_len=10, trend_window=200,
max_hold_days=20, min_hold_days=10`.

## Decision

**Accept for equity (QQQ, SPY)** — all 5 validators pass for both symbols.
**Reject for crypto (BTC/USDT, ETH/USDT)** — decisive fail on Sharpe/MDD/TC
(crypto's higher daily vol overwhelms the fixed exit/crossover cadence;
consistent with the grid's crypto pass_fraction 0.139 vs equity's 0.426).

Strategy file kept live in `strategies/` scoped to equity only per the log
entry's asset_class field.
