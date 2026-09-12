# ATR-Adaptive-Gamma Laguerre Filter trend following

**Strategy file:** `strategies/2026-09-13_atr_adaptive_laguerre_filter.py`
**Hypothesis id:** 2026-09-13-033

## Source

runbacktest.com's "Adaptive Laguerre Filter" strategy doc
(https://runbacktest.com/trading-strategies/adaptive-laguerre-filter), read
this iteration via browser_exec -- `web_search` (DDGS backend) returned
"No results found" on the first query attempted this iteration, so the
Bing SERP fallback was used for the whole iteration.

Disclosed rule: EMA-based ATR normalized to a percentage of price drives
gamma between `gamma_max` (smooth, low-vol regimes) and `gamma_min`
(responsive, high-vol regimes) via an `atr_threshold_percent` normalizer;
the four-pole Laguerre filter is computed sequentially with that
per-bar-varying gamma, and price-vs-filter crossovers plus slope
confirmation drive entries/exits.

This is distinct from the already-accepted 2026-09-05-058 Adaptive
Laguerre Filter, which used Ehlers' own instantaneous-phase feedback
mechanism to adapt gamma (not ATR%-driven) -- here gamma tracks realized
volatility regime directly rather than cycle-phase feedback.

## Grid test (Step 6)

`atr_threshold_percent` in [2.0,3.0,5.0] x `slope_lookback` in [3,5,8],
equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), vol_regime_splits=3 -> 108
cells.

- pass_fraction: 0.213 (23/108)
- by_asset_class: equity 23/54, crypto 0/54
- by_vol_regime: low 18/36, mid 5/36, high 0/36
- best_cell: QQQ, atr_threshold_percent=5.0/slope_lookback=5, low-vol, Sharpe=3.010
- worst_cell: QQQ, atr_threshold_percent=2.0/slope_lookback=3, high-vol, Sharpe=-0.508

Crypto rejected decisively (0/54) -- consistent with this repo's broader
finding that Ehlers/Laguerre-family adaptive smoothers built on daily
equity-style volatility characteristics don't transfer to BTC/ETH.

## Single-config validation (Step 7)

Per-symbol fine parameter search (atr_threshold_percent x slope_lookback x
max_hold_days):

**QQQ** (atr_threshold_percent=5.0, slope_lookback=5, max_hold_days=20):

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.660 | >=1.0 | Yes |
| Max drawdown | 0.152 | <=0.25 | Yes |
| TC survival (net Sharpe, 10bps/trade, 101 trades) | 1.482 | >=0.5 | Yes |
| Walk-forward (4 splits) | 1.0 (4/4) | >=0.75 | Yes |
| Parameter sensitivity (rel std, 20-combo local sweep) | 0.178 | <=0.5 | Yes |

**SPY** (atr_threshold_percent=2.0, slope_lookback=8, max_hold_days=30):

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.131 | >=1.0 | Yes |
| Max drawdown | 0.101 | <=0.25 | Yes |
| TC survival (net Sharpe, 10bps/trade, 114 trades) | 0.856 | >=0.5 | Yes |
| Walk-forward (4 splits) | 1.0 (4/4) | >=0.75 | Yes |
| Parameter sensitivity (rel std, 16-combo local sweep) | 0.253 | <=0.5 | Yes |

All 5 validators pass cleanly for both symbols with independently tuned
configs (QQQ needs a much higher atr_threshold_percent, i.e. runs "smoother"
on average, than SPY).

## Outcome

**Accepted for QQQ and SPY** (per-symbol tuned configs above). Crypto
(BTC/USDT, ETH/USDT) rejected decisively per the grid test.
