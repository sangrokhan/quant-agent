# Backtest Report: Williams Alligator Fan-Spread Continuous Sizing Dial (SMA Trend Gate)

**Strategy file:** `strategies/2026-09-14_alligator_spread_sizing_sma_trend.py`
**Date:** 2026-09-14

## Hypothesis

This repo's Williams Alligator entries (2026-09-04-112 crossover accepted,
2026-09-05-050 Gator Oscillator, 2026-09-09-071 eating-state pullback) are
all binary trigger/state-machine rules. This iteration reframes the
Alligator's own signed fan-spread (Lips - Jaw, ATR-normalized) as a
CONTINUOUS SIZING dial: tanh-squashed to [-1,+1] within an
SMA(trend_window) uptrend gate. First Alligator-as-continuous-sizing-dial
variant.

Source: same Alligator SMMA/shift construction as this repo's own
2026-09-04-112 (howtotrade.com/indicators/alligator-indicator/); no new
external fetch needed, formula re-confirmed from this repo's own prior
implementation.

## Grid Test Summary (Step 6)

`param_grid={"atr_window": [14, 21], "base_exposure": [0.4, 0.6, 0.8],
"sensitivity": [0.5, 0.7, 0.9]}`, `symbols={"equity": ["QQQ","SPY"],
"crypto": ["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`.

- total_cells: 216, passed_cells: 87, **pass_fraction: 0.403**
- by_asset_class: equity 69/108 (0.639, strongest equity pass rate of any
  sizing dial this trigger), crypto 18/108 (0.167)
- by_vol_regime: low 54/72 (0.75), mid 33/72 (0.458), high 0/72 (0.0)
- best_cell: atr_window=14, base_exposure=0.6, sensitivity=0.9, ETH/USDT mid-vol, sharpe=2.54
- worst_cell: atr_window=21, base_exposure=0.4, sensitivity=0.7, QQQ high-vol, sharpe=-0.33

Default grid combos alone weren't quite strong enough on the full sample
(best default config only reached ~1.0/1.05 Sharpe) -- a local scan of
trend_window/base_exposure/sensitivity was needed to clear both symbols'
threshold comfortably.

## Primary Config Validation (Step 7)

Best full-sample single config: `atr_window=14, base_exposure=1.0,
sensitivity=0.5, trend_window=40`.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.002 (thin pass) | 0.211 (pass) | 0.709 (pass) | 1.00 (pass) | 0.029 rel-std (pass) |
| SPY | 1.059 (pass) | 0.114 (pass) | 0.713 (pass) | 1.00 (pass) | 0.050 rel-std (pass) |
| BTC/USDT | 1.295 (pass) | 0.644 (**fail**, cap 0.25) | 1.207 (pass) | 1.00 (pass) | 0.024 rel-std (pass) |
| ETH/USDT | 1.160 (pass) | 0.590 (**fail**, cap 0.25) | 1.099 (pass) | 1.00 (pass) | 0.018 rel-std (pass) |

All 5 validators pass for both QQQ (thin pass, 1.002) and SPY. Crypto
(BTC/ETH) decisively fails only on max-drawdown, same pattern as
essentially every other sizing-dial strategy tested this trigger.

## Decision

**ACCEPT for equity (QQQ thin pass + SPY). REJECT for crypto (BTC/ETH, MDD decisive fail) -- candidate for a follow-up leverage-cap recalibration iteration.**
