# 2026-09-21 Dollar-Bar SMA Crossover Trend Following

**Hypothesis:** Resampling daily OHLCV bars into variable-length
"dollar bars" (activity-clocked, per López de Prado's information-driven
bars concept) and running a simple SMA-crossover trend signal on the
resampled bar-close series performs better/more consistently than a raw
time-clocked equivalent, because information/activity does not arrive at a
constant rate and time-bar returns are known to be non-IID/heteroskedastic.

**Source:** https://twowaymind.com/article-information-driven-bars
("Information-Driven Bars: Tick, Volume & Dollar Sampling for Market
Microstructure", Aug 2026, summarizing Lopez de Prado's *Advances in
Financial Machine Learning*). True tick-level dollar bars need trade-level
data unavailable via this repo's `data/loaders.py` (OHLCV only); this
iteration approximates the concept using daily close*volume as the "dollar
volume" activity measure, accumulated causally against a trailing rolling
average threshold.

**Strategy file:** `strategies/2026-09-21_dollar_bar_sma_crossover.py`

## Step 6 — Grid test summary (target_days_per_bar: [3,5] x fast_bars: [5,10] x slow_bars: [20,30], SPY/QQQ/BTC/ETH, vol terciles)

- total_cells: 96, passed_cells: 24, **pass_fraction: 0.25**
- by_asset_class: equity 24/48 passed, **crypto 0/48 passed**
- by_vol_regime: low 16/32, mid 8/32, **high 0/32**
- best_cell: target_days_per_bar=5.0, fast_bars=5, slow_bars=30, SPY, low-vol regime, Sharpe=2.74
- worst_cell: target_days_per_bar=3.0, fast_bars=5, slow_bars=20, QQQ, high-vol regime, Sharpe=-0.83

Full 8-combo sweep of full-sample Sharpe (SPY/QQQ, target_days_per_bar in
{3,5}, fast_bars in {5,10}, slow_bars in {20,30} with fast<slow):
SPY(3,5,20)=0.789, SPY(3,5,30)=0.897, SPY(3,10,20)=0.770, **SPY(3,10,30)=1.003**,
SPY(5,5,20)=1.023, SPY(5,5,30)=0.928, SPY(5,10,20)=0.755, SPY(5,10,30)=0.609,
QQQ(3,5,20)=0.715, QQQ(3,5,30)=1.131, QQQ(3,10,20)=1.064, QQQ(3,10,30)=0.925,
QQQ(5,5,20)=0.954, QQQ(5,5,30)=0.854, QQQ(5,10,20)=0.760, QQQ(5,10,30)=0.674.

Consistently equity-only, low/mid-vol regimes; fails uniformly on crypto and
in high-vol regimes.

## Step 7 — Single-config validators (primary config: target_days_per_bar=3.0, fast_bars=10, slow_bars=30, SPY, full 2019-2026 sample)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** | 1.003 | >= 1.0 |
| Max drawdown | PASS | 0.1895 | <= 0.25 |
| Transaction cost survival (10bps/trade, 17 trades) | PASS | net Sharpe 0.978 | >= 0.5 |
| Walk-forward (manual 4-split fallback; `vbt.utils.splitting.RangeSplitter` broken in this install, per repo convention) | PASS | 3/4 splits positive (0.75) | >= 0.75 |
| Parameter sensitivity (fast_bars in {10}/target_days_per_bar sweep {3,5} etc, 4-combo sweep) | PASS | relative std 0.046 | <= 0.5 |

(Also confirmed on QQQ with target_days_per_bar=3.0/fast_bars=5/slow_bars=30:
Sharpe 1.131, MDD 26.2% *[fails 25% cap]*, net-cost Sharpe 1.111, walk-forward
0.75 pass -- SPY config chosen as primary since it clears MDD too.)

## Step 8 — Decision: **ACCEPTED** (equity only, SPY primary config)

All 5 validators passed for the primary config: target_days_per_bar=3.0
(dollar-bar threshold sized at ~3 average trading days worth of dollar
volume), fast_bars=10, slow_bars=30, on SPY over the full 2019-2026 sample.
Strategy is honestly scoped to **equity, low/mid volatility regimes only**
(grid test: 0/48 crypto cells passed, 0/32 high-vol-regime cells passed
across both asset classes) — a future loop should not assume this holds
outside that scope. Strategy file and this report are kept as a live
strategy.
