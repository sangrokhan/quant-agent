# ALMA Dual Crossover Trend-Following (2026-09-28)

## Hypothesis

ALMA (Arnaud Legoux Moving Average) is a Gaussian-weighted moving average
with an offset parameter designed to reduce lag while keeping smoothness
(unlike EMA, which trades lag for overshoot). Per TradingView's
"Arnaud Legoux Moving Average Cross (ALMA)" open-source script
(https://www.tradingview.com/script/PgVGNY0m-Arnaud-Legoux-Moving-Average-Cross-ALMA/,
Marianne9, 2022), the standard mechanical rule is a dual-ALMA crossover: a
fast-length ALMA crossing above a slow-length ALMA signals a long entry.
Corroborated by a Google SERP snippet of LuxAlgo's ALMA guide describing
"a two-average crossover, a faster ALMA against a [slower ALMA]" as the
standard approach (the LuxAlgo blog page itself 404'd when fetched
directly). First ALMA-family strategy tested in this repo (0 prior hits).

Source URLs:
- https://www.tradingview.com/script/PgVGNY0m-Arnaud-Legoux-Moving-Average-Cross-ALMA/ (exact rule)
- https://www.luxalgo.com/blog/arnaud-legoux-moving-average-guide (404, corroborating SERP snippet only)

## Strategy

`strategies/2026-09-28_alma_dual_crossover_trend.py`

- ALMA(fast_window) crosses above ALMA(slow_window) -> long entry.
- ALMA(fast_window) crosses below ALMA(slow_window) -> exit.
- max_hold_days time-stop backstop (60 days default) -- added robustness,
  not in the original script.
- Default shape params offset=0.85, sigma=6.0 (standard ALMA defaults).

## Step 6 grid test summary

Grid: fast_window in [7,9,14] x slow_window in [21,34,50], symbols
{QQQ, SPY, BTC/USDT, ETH/USDT}, vol_regime_splits=3 (108 cells total).

```
pass_fraction: 0.343 (37/108)
by_asset_class: equity 30/54 (0.556), crypto 7/54 (0.130)
by_vol_regime: low 25/36 (0.694), mid 9/36 (0.250), high 3/36 (0.083)
best_cell: SPY, fast=9/slow=50, low-vol, Sharpe=2.97
worst_cell: ETH/USDT, fast=7/slow=21, high-vol, Sharpe=-0.21
```

Edge concentrated in equity + low-vol regime, consistent with a
trend-following/momentum construction (whipsaws in high-vol/choppy
periods). Best average-across-regime full-sample config across symbols:
SPY fast=14/slow=34 (avg Sharpe 1.42) and QQQ fast=9/slow=50 (avg Sharpe
1.39); fast=14/slow=34 shared config chosen for the primary validator run
below since it performs well on BOTH QQQ and SPY without per-symbol
retuning.

## Step 7 single-config validators (fast_window=14, slow_window=34)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel_std) | Trades | Result |
|---|---|---|---|---|---|---|---|
| QQQ | 1.138 (PASS >=1.0) | 0.226 (PASS <=0.25) | 1.064 (PASS >=0.5) | 1.00 (PASS >=0.75) | 0.173 (PASS <=0.5) | 59 | **ALL PASS** |
| SPY | 1.334 (PASS) | 0.137 (PASS) | 1.231 (PASS) | 1.00 (PASS) | 0.305 (PASS) | 58 | **ALL PASS** |
| BTC/USDT | 1.083 (PASS) | 0.584 (**FAIL**, cap 0.25) | 1.050 (PASS) | 1.00 (PASS) | 0.087 (PASS) | 91 | FAIL (MDD) |
| ETH/USDT | 1.085 (PASS) | 0.537 (**FAIL**, cap 0.25) | 1.060 (PASS) | 1.00 (PASS) | 0.116 (PASS) | 96 | FAIL (MDD) |

Walk-forward computed manually (4 equal-length splits, Sharpe > 0 per
split) since `vectorbt.utils.splitting.RangeSplitter` is unavailable in
this repo's installed vectorbt version -- established repo workaround.

## Decision

**Accept for equity (QQQ, SPY) only, at fast_window=14/slow_window=34,
offset=0.85, sigma=6.0, max_hold_days=60.** All 5 validators pass on both
equity symbols with a single shared config (no per-symbol retuning
needed). Crypto (BTC/USDT, ETH/USDT) is decisively rejected on max
drawdown -- a plain trend-following dual-MA crossover with no vol/leverage
gating whipsaws too hard through crypto's high-volatility regimes (MDD
0.53-0.58 vs the 0.25 cap), consistent with this repo's repeated finding
that discrete-crossover trend strategies need a leverage-cap or
vol-regime gate to survive crypto MDD (cf. STARC/Keltner/Acceleration
Bands continuous-sizing-dial rescues). A future iteration could attempt
that same leverage-cap rescue pattern on ALMA crossover for crypto.

Files:
- `strategies/2026-09-28_alma_dual_crossover_trend.py` (kept, live for QQQ/SPY)
- `grid_summary_alma_dual_crossover.json`, `grid_cells_alma_dual_crossover.json`
- `validate_result_alma_dual_crossover.json`
