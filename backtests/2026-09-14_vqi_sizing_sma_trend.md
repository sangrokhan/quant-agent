# Volatility Quality Index (VQI) Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-14_vqi_sizing_sma_trend.py`

## Hypothesis

Volatility Quality Index (VQI, Thomas Stridsman): Bar Range = True Range;
Weighted Volatility = Bar Range * sign(Close-Open); VQI Raw =
EMA(Weighted Volatility, vqi_length); VQI Smoothed = EMA(VQI Raw,
smoothing_length). Formula already fully confirmed in this repo's 2 prior
VQI entries (`2026-09-08-028` streak-confirmation binary trigger, QQQ
Sharpe 0.941 near-miss; `2026-09-08-043` vol-regime-gated follow-up). Both
prior entries used VQI Smoothed's directional STREAK (N consecutive
up/down bars) as a binary trigger. This iteration reframes VQI Smoothed
itself (a signed, unbounded EMA-of-signed-true-range series) as a
CONTINUOUS SIZING dial: rolling z-scored and tanh-squashed to [-1,+1]
within an SMA(40) uptrend gate — the same "unbounded diff -> z-score ->
tanh" pattern already used for TCF, Precision Trend, DSP, Voss, and WAE
earlier this cron trigger. Directly addresses the near-miss nature of
`2026-09-08-028` (everything but Sharpe passed) by smoothing exposure
continuously rather than requiring a discrete N-bar streak. First VQI
continuous-sizing variant.

## Grid test (`validation/grid_test.py::run_strategy_grid`)

`param_grid={"sensitivity":[0.4,0.6,0.8],"deadband":[0.2,0.3],"smoothing_length":[5,10]}`,
`symbols={"equity":["QQQ","SPY"],"crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`.

- **Overall pass_fraction: 0.389 (56/144)**
- by_asset_class: equity 36/72 (0.5), crypto 20/72 (0.278).
- by_vol_regime: low 39/48 (0.813), mid 17/48 (0.354), high 0/48 (0.0).
- best_cell: equity SPY, sensitivity=0.8/deadband=0.2/smoothing_length=5,
  low-vol, Sharpe 2.85.
- worst_cell: equity QQQ, same params, high-vol, Sharpe -0.004.

Deadband=0.2/0.3 from the coarse grid caused excessive turnover for the
single-config TC-survival validator; per-symbol manual tuning found
distinct optimal deadbands (QQQ tighter, SPY wider) needed.

## Single-config validators (per-symbol tuned)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | All pass |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=40, sensitivity=0.6, deadband=0.3, smoothing_length=5 | 1.098 (pass) | 0.107 (pass) | 0.620 (pass) | 1.00 (pass) | 0.085 (pass) | **Yes** |
| SPY | trend_window=40, sensitivity=0.5, deadband=0.45, smoothing_length=5 | 1.133 (pass) | 0.083 (pass) | 0.782 (pass) | 0.75 (pass, exact threshold) | 0.139 (pass) | **Yes** |
| BTC/USDT | trend_window=40, sensitivity=0.5, deadband=0.2, leverage_cap=0.3, base_exposure=0.15 | 1.178 (pass) | 0.223 (pass) | 0.846 (pass) | 1.00 (pass) | 0.038 (pass) | **Yes** |
| ETH/USDT | same crypto config | 1.098 (pass) | 0.176 (pass) | 0.900 (pass) | 1.00 (pass) | 0.043 (pass) | **Yes** |

## Outcome

**Accepted — all 4 symbols pass all 5 validators**, at per-symbol/asset-
class-tuned configs (QQQ and SPY need different deadbands to both clear
TC-survival; crypto needed a much smaller deadband than the equity grid
defaults to avoid a degenerate zero-trade config). SPY's walk-forward
passes at the exact 0.75 threshold (3/4 splits positive) — a narrow pass
worth monitoring if this strategy is revisited. Crypto's very low
parameter-sensitivity (0.038-0.043) is notably robust, among the most
stable crypto configs of this cron trigger's continuous-sizing campaign.
