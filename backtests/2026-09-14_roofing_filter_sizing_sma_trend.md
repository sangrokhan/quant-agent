# Ehlers Roofing Filter Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-14_roofing_filter_sizing_sma_trend.py`

## Hypothesis

John Ehlers' Roofing Filter (2-pole high-pass filter strips slow
trend/drift longer than `hp_period` bars, then a 2-pole SuperSmoother
low-pass filter strips fast noise shorter than `lp_period` bars, TASC
2013), formula already fully confirmed and reused verbatim from this
repo's existing entries `strategies/2026-09-05_roofing_filter_signal_crossover.py`
and `strategies/2026-09-12_ehlers_roofing_filter_signalcross.py` (per
`https://theindicatorlab.com/reviews/ehlers-roofing-filter/`). Both prior
repo entries used RF-crosses-its-own-3-period-SMA-signal-line as a BINARY
entry trigger — both REJECTED. This iteration reframes the Roofing
Filter's own output (a zero-centered, cycle-bandpassed oscillator) as a
CONTINUOUS SIZING dial: rolling z-scored and tanh-squashed to [-1,+1]
within an SMA(trend_window) uptrend gate — the same pattern used for TCF,
Precision Trend, DSP, Voss, WAE, and VQI earlier this cron trigger. First
Ehlers Roofing Filter continuous-sizing variant.

## Grid test (`validation/grid_test.py::run_strategy_grid`)

`param_grid={"sensitivity":[0.4,0.6,0.8],"deadband":[0.2,0.3],"lp_period":[12,20]}`,
`symbols={"equity":["QQQ","SPY"],"crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`.

- **Overall pass_fraction: 0.438 (63/144)**
- by_asset_class: equity 33/72 (0.458), crypto 30/72 (0.417) — unusually
  balanced across asset classes for this cron trigger's campaign.
- by_vol_regime: low 41/48 (0.854), mid 18/48 (0.375), high 4/48 (0.083).
- best_cell: equity QQQ, sensitivity=0.4/deadband=0.3/lp_period=12,
  low-vol, Sharpe 2.75.
- worst_cell: crypto ETH/USDT, sensitivity=0.6/deadband=0.3/lp_period=12,
  high-vol, Sharpe 0.15.

## Single-config validators (per-symbol tuned)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | All pass |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=40, sensitivity=0.4, deadband=0.3, lp_period=12 | 1.118 (pass) | 0.125 (pass) | 0.624 (pass) | 1.00 (pass) | 0.079 (pass) | **Yes** |
| SPY | trend_window=40, sensitivity=0.4, deadband=0.4, lp_period=12 | 1.269 (pass) | 0.075 (pass) | 0.847 (pass) | 1.00 (pass) | 0.087 (pass) | **Yes** |
| BTC/USDT | trend_window=40, sensitivity=0.3, deadband=0.15, leverage_cap=0.35, base_exposure=0.175, lp_period=16 | 1.315 (pass) | 0.212 (pass) | 0.902 (pass) | 1.00 (pass) | 0.096 (pass) | **Yes** |
| ETH/USDT | trend_window=40, sensitivity=0.4, deadband=0.2, leverage_cap=0.25, base_exposure=0.125, lp_period=12 | 1.127 (pass) | 0.132 (pass) | 0.852 (pass) | 1.00 (pass) | 0.536 (**fail**, >0.5) | No |

## Outcome

**Partial accept: QQQ, SPY, BTC/USDT all pass all 5 validators. ETH/USDT
rejected — parameter-sensitivity fail (0.536 vs 0.5 threshold).** This
rescues a previously twice-rejected indicator family via the continuous-
sizing reframing, generalizing across both asset classes with only one
crypto symbol (ETH) not clearing the bar — flagged as a candidate for a
future ETH-specific recalibration (e.g. narrower lp_period sweep).
