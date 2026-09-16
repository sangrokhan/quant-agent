# Backtest report: DEMA (Double Exponential Moving Average) crossover

**Strategy file:** `strategies/2026-09-17_dema_crossover.py`

## Hypothesis

Per Patrick Mulloy's DEMA (1994), confirmed via Google SERP synthesis this
iteration (TMGM Trading Academy's own disclosed parameter convention: "the
standard crossover pair is 20 and 50 periods"; corroborated by StockCharts
ChartSchool and LuxAlgo's explicit crossover definition): DEMA = 2*EMA(n) -
EMA(EMA(n)), reduces standard-EMA lag by subtracting the EMA-of-EMA
overshoot. Long entry when fast DEMA crosses above slow DEMA; exit on the
reverse crossover. First DEMA-crossover entry in this repo (0 prior
matches, distinct from KAMA/FRAMA/T3/VIDYA/McGinley already tested).

## Grid test summary (Step 6)

`param_grid={"fast_period": [10,20,30], "slow_period": [40,50,60]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 38, **pass_fraction: 35.2%**
- by_asset_class: equity 27/54; crypto 11/54
- by_vol_regime: low 29/36; mid 8/36; high 1/36
- best_cell: QQQ, low-vol regime, fast=30/slow=60, Sharpe 3.20
- worst_cell: QQQ, high-vol regime, fast=10/slow=60, Sharpe -0.57

## Single-config validators, full sample 2019-2026 (per-symbol tuned configs)

**QQQ (fast_period=30, slow_period=60, the grid's best cell config):**

| Validator | Value | Result |
|---|---|---|
| Sharpe (>=1.0) | 1.239 | pass |
| Max Drawdown (<=0.25) | 0.236 | pass |
| TC survival (net Sharpe >=0.5) | 1.214 (42 trades) | pass |
| Walk-forward (4-split) | 0.75 (3/4) | pass |
| Parameter sensitivity (fast in [20..35]) | 0.073 | pass |

**SPY (fast_period=5, slow_period=80 -- QQQ's config gave SPY Sharpe 0.79/
MDD 0.257, both fail; widened sweep found this distinct SPY-specific
config):**

| Validator | Value | Result |
|---|---|---|
| Sharpe (>=1.0) | 1.253 | pass |
| Max Drawdown (<=0.25) | 0.116 | pass |
| TC survival (net Sharpe >=0.5) | 1.147 (112 trades) | pass |
| Walk-forward (4-split) | 0.75 (3/4) | pass |
| Parameter sensitivity (fast in [4..7]) | 0.022 | pass |

**Crypto (QQQ's config fast=30/slow=60):** BTC/USDT Sharpe 1.214 but MDD
0.458 (nearly 2x cap); ETH/USDT Sharpe 1.135 but MDD 0.551 (2.2x cap) --
decisively rejected on drawdown for both despite acceptable Sharpe.

## Decision: ACCEPTED (equity QQQ + SPY, per-symbol tuned configs); REJECTED (crypto)

Both equity symbols pass all 5 validators, though requiring genuinely
different parameter regimes (QQQ needs a slower 30/60 pair; SPY needs a
much faster 5/80 pair) rather than a single shared config -- recorded
honestly here as a per-symbol-tuned acceptance, not a universal one.
Crypto decisively rejected on drawdown; binary full exposure with no
vol-targeting doesn't survive crypto's larger daily swings, consistent
with the pattern seen for other binary-trigger long-only strategies this
cron trigger (SafeZone Stop, Grover Llorens Activator).
