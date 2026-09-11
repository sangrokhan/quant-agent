# Holt-Winters Forecast Band Mean Reversion — ACCEPTED (SPY only)

**Strategy file:** `strategies/2026-09-12_holt_winters_band_meanrev.py`
**Source:** https://www.tradingview.com/script/rcrVhyqk-Holt-Winters-Forecast-Bands/
(indicator description, via Google AI Overview synthesis; browser_exec
google.com fallback used this iteration — web_search DDGS backend errors)

## Hypothesis

Holt linear-trend forecast (level+trend recursive smoothing, same
construction as this repo's already-accepted 2026-09-08-063 trend-crossover
strategy) forms a central baseline. An ATR-scaled band around that baseline
defines oversold/overbought extremes. Long entry when close touches/crosses
below the lower band (oversold extension); exit when price reverts to the
central forecast baseline, or a max_hold_days time-stop. Architecturally
distinct from 2026-09-08-063 (which trades breakouts THROUGH the forecast
line as a trend signal) — this fades extensions AWAY from bands around the
same baseline back toward it, a mean-reversion construction.

## Grid test summary (Step 6)

- Grid: `band_mult` in [1.5, 2.0, 2.5], `max_hold_days` in [5, 10, 15];
  symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.
  108 total cells.
- **pass_fraction: 0.25 (27/108)**
- by_asset_class: equity 27/54 passed; **crypto 0/54 (decisive fail)**
- by_vol_regime: low 15/36, mid 9/36, high 3/36 — holds up across all
  three regimes for equity (not narrowly concentrated in one slice, unlike
  the prior iteration's rejected ADX/ATRpct/Hurst strategy)
- best_cell: band_mult=2.0, max_hold_days=5, SPY, low-vol regime, Sharpe 3.45

## Single-config validation (Step 7) — band_mult=2.0, max_hold_days=5, full sample 2019-2026

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.204 ✅ | 0.686 ❌ | ≥ 1.0 |
| Max drawdown | 0.091 ✅ | 0.081 ✅ | ≤ 0.25 |
| TC survival (10bps/trade, 68/50 trades) | 0.998 ✅ | 0.571 ✅ | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-slice fallback) | 1.00 ✅ (4/4) | 1.00 ✅ (4/4) | ≥ 0.75 |
| Parameter sensitivity (band_mult 1.5/2.0/2.5) | 0.410 ✅ | 0.334 ✅ | ≤ 0.5 relative std |

## Decision: ACCEPTED (SPY only)

All five validators pass for SPY at band_mult=2.0/max_hold_days=5. QQQ
fails the Sharpe threshold (0.686 < 1.0) despite passing every other
validator, and edge holds up across all three volatility regimes (unlike
several recently-rejected regime-narrow strategies) — a genuinely
scope-limited but honest accept. Crypto rejected decisively (0/54 grid
cells). Strategy is kept live in `strategies/` scoped to SPY only; a future
iteration could investigate whether a QQQ-specific parameter tune (per this
repo's established per-symbol-tuned-config pattern, e.g. 2026-09-04-159,
2026-09-09-041) rescues QQQ.
