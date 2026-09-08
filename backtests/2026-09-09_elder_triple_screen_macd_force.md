# Backtest report: Elder Triple Screen (MACD-Histogram trend + Force Index pullback) (REJECTED)

**Strategy file:** `strategies/2026-09-09_elder_triple_screen_macd_force.py`

## Hypothesis

Per a Google-surfaced snippet of the "Alexander Elder Triple Screen Trading
System" reference PDF (via search "Elder Triple Screen weekly MACD
histogram daily force index entry rule"; the original PDF page itself was
not directly fetchable -- Investopedia/FBS/QuantifiedStrategies/AlphaX/
Elearnmarkets pages either lacked the numeric rule or 404'd): "When the
weekly MACD-Histogram rises, [look for] the 2-day EMA of Force Index [to
dip negative, signaling a pullback-buy]." Adapted to this repo's daily-only
data: a longer-period MACD-Histogram(60/130/45) proxies the "weekly" trend
screen; a 2-day EMA of Force Index (volume-weighted momentum) dipping
below/above zero times entries within that trend. First Elder Triple
Screen strategy in this repo.

## Step 6 grid summary (run_strategy_grid)

- param_grid: `force_index_ema=[2,3,5]` x `max_hold_days=[10,20,30]`
- symbols: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- vol_regime_splits=3
- **total_cells=108, passed_cells=12, pass_fraction=0.111**
- by_asset_class: equity 12/54, crypto 0/54
- by_vol_regime: low 9/36, mid 3/36, high 0/36
- best_cell: force_index_ema=2, max_hold_days=20, QQQ low-vol, Sharpe=1.46
- worst_cell: force_index_ema=2, max_hold_days=30, QQQ high-vol, Sharpe=-0.82

Weak overall: only 11% of cells passed, concentrated in equity/low-vol; zero
passes on crypto or high-vol regimes.

## Single-config validation (best grid cell: force_index_ema=2, max_hold_days=20), full sample

| Symbol | Sharpe | MDD | TC-survival | Param sensitivity |
|---|---|---|---|---|
| QQQ | 0.421 (fail, thresh 1.0) | 0.201 (pass) | 0.311 (fail, thresh 0.5) | 0.237 rel-std (pass) |
| SPY | 0.306 (fail, thresh 1.0) | 0.192 (pass) | 0.137 (fail, thresh 0.5) | 0.422 rel-std (pass) |

MDD and parameter sensitivity pass comfortably on both symbols, but Sharpe
and transaction-cost survival fail decisively on both (positive but well
below thresholds), driven by moderate trade frequency (52-62 trades over
7.5yr) eroding a modest raw edge.

## Outcome: REJECTED

Rejected: 2 of 4 validators fail on both symbols at full sample (Sharpe well
below 1.0, net-of-cost Sharpe well below 0.5), and the grid confirms a
narrow, weak edge (11% pass fraction, equity/low-vol only, 0% on crypto and
high-vol). Not a near-miss -- Sharpe misses by more than half the threshold
gap on both symbols. The daily-bar single-MACD proxy for the source's
genuine weekly-timeframe trend screen may be diluting the intended
multi-timeframe signal quality; a true weekly-resampled trend screen (if
this repo's loaders supported non-daily resampling) could be worth
revisiting in a future iteration.
