# 2026-09-05 — OBV + Donchian Dual Breakout (QQQ/SPY, crypto)

## Hypothesis
Per TrendSpider's "On-Balance Volume Trading Strategies"
(https://trendspider.com/learning-center/on-balance-volume-trading-strategies/,
"Breakout Strategy" section): a price breakout is more likely genuine when
OBV is *simultaneously* breaking its own analogous rolling high (volume
confirms the price move). Tested: long when close breaks above its own
`entry_window`-day rolling high AND OBV breaks above its own
`entry_window`-day rolling high on the same bar; exit on close breaking
below its own `exit_window`-day rolling low, or a `max_hold_days` time-stop.

## Grid test (validation/grid_test.py, run_strategy_grid)
- `param_grid`: entry_window in [15,20,30], exit_window in [8,10,15]
  (max_hold_days fixed at 15)
- symbols: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
- vol_regime_splits=3 (low/mid/high realized-vol terciles)
- 108 total cells, **18 passed (pass_fraction = 0.167)**
- by_asset_class: equity 18/54 passed; **crypto 0/54 passed** (decisive reject)
- by_vol_regime: low 15/36; mid 1/36; high 2/36 — edge is concentrated almost
  entirely in low-vol regimes
- best_cell: entry_window=15, exit_window=15, QQQ, low-vol, Sharpe=2.04
- worst_cell: entry_window=30, exit_window=15, SPY, mid-vol, Sharpe=-1.12

## Single-config validation (entry_window=15, exit_window=8, max_hold_days=15)

| Metric | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe (full period) | 0.906 (FAIL) | 0.763 (FAIL) | >= 1.0 |
| Max drawdown | 0.097 (PASS) | 0.141 (PASS) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.731 (PASS) | 0.639 (PASS) | >= 0.5 |
| Walk-forward (manual 4-split, vbt splitter bug workaround) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |

Walk-forward note: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (consistent with other recent log entries) — used a manual
4-contiguous-chunk date split instead, checking each chunk's Sharpe > 0.

## Decision: REJECTED
Full-sample Sharpe fails the >=1.0 threshold on both QQQ and SPY at the
best full-period param combo found in the grid search
(entry_window=15/exit_window=8), even though MDD/TC-survival/walk-forward
all pass and low-vol-regime slices look strong (Sharpe up to 2.04). The
edge is real but narrow — concentrated in low-vol regimes only — and does
not clear the bar unconditionally across the full sample. Crypto rejected
decisively (0/54 grid cells) — the dual price+OBV breakout confirmation
does not translate to BTC/USDT or ETH/USDT at any tested parameter/vol-regime
combination.

## Notes for future iterations
A regime-gated variant (only trade this breakout rule during low-vol
terciles, flat otherwise) would likely clear the Sharpe bar given the
low-vol subgrid pass rate (15/36) — worth revisiting with an explicit
vol-regime filter added to the entry condition, similar to the existing
`2026-09-03_bb_meanrev_qqq_volregime.py` pattern.
