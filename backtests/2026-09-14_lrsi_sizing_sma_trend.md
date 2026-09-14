# Ehlers Laguerre RSI (LRSI) Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-14_lrsi_sizing_sma_trend.py`

## Hypothesis

Ehlers Laguerre RSI (4-stage recursive Laguerre filter L0-L3, RSI-style
logic applied to the filtered levels, naturally bounded [0,1]) per
`https://www.quantifiedstrategies.com/laguerre-rsi/`: "Using Zero Line (0.5)
as Momentum Bias: When the Laguerre RSI stays above 0.5, momentum is
bullish. Below 0.5 indicates bearish momentum." Repo has 4 prior LRSI
entries (`2026-09-05-053` binary mean-reversion threshold, rejected;
`2026-09-06-110` binary >0.5/<=0.5 regime filter; `2026-09-05-058` Adaptive
Laguerre Filter variant; `2026-09-12-173` Ehlers Continuation Index
derivative), none using LRSI's own [0,1]-bounded value as a CONTINUOUS
sizing dial. This iteration directly rescales LRSI to [-1,+1] around its
own 0.5 zero line and uses it as a sizing dial within an SMA(trend_window)
uptrend gate — the same "naturally-bounded oscillator -> direct rescale ->
sizing dial" pattern already used for DVO, EBSW, VoRSI, and the Elegant
Oscillator earlier this cron trigger. First LRSI continuous-sizing variant.

## Grid test (`validation/grid_test.py::run_strategy_grid`)

`param_grid={"gamma":[0.4,0.5,0.6],"sensitivity":[0.4,0.6,0.8],"deadband":[0.2,0.3]}`,
`symbols={"equity":["QQQ","SPY"],"crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`.

- **Overall pass_fraction: 0.361 (78/216)**
- by_asset_class: equity 56/108 (0.519), crypto 22/108 (0.204) — equity much
  stronger.
- by_vol_regime: low 48/72 (0.667), mid 30/72 (0.417), high 0/72 (0.0) —
  fully fails in the high-vol tercile across the board.
- best_cell: equity SPY, gamma=0.6/sensitivity=0.8/deadband=0.2, low-vol,
  Sharpe 2.40.
- worst_cell: equity QQQ, gamma=0.5/sensitivity=0.4/deadband=0.3, high-vol,
  Sharpe -0.004.

## Single-config validators

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | All pass |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=40, gamma=0.6, sensitivity=0.8, deadband=0.3 | 1.146 (pass) | 0.154 (pass) | 0.723 (pass) | 1.00 (pass) | 0.081 (pass) | **Yes** |
| SPY | same | 1.111 (pass) | 0.111 (pass) | 0.608 (pass) | 1.00 (pass) | 0.085 (pass) | **Yes** |
| BTC/USDT | trend_window=40, gamma=0.6, sensitivity=0.4, deadband=0.2, leverage_cap=0.25, base_exposure=0.125 | 1.119 (pass) | 0.247 (pass, narrow) | 0.790 (pass) | 1.00 (pass) | 0.486 (pass, narrow) | **Yes** |
| ETH/USDT | same crypto config | 1.016 (pass) | 0.114 (pass) | 0.801 (pass) | 1.00 (pass) | 0.509 (**fail**, >0.5 narrow) | No |

## Outcome

**Partial accept: QQQ, SPY, BTC/USDT all pass all 5 validators. ETH/USDT
rejected — narrow parameter-sensitivity near-miss (0.509 vs 0.5
threshold).**

BTC/USDT's own MDD (0.247) and parameter-sensitivity (0.486) both sit
close to their thresholds too — a genuine narrow pass, not a decisive one.
This entry is flagged as a good candidate for a future ETH-specific
leverage-cap/sensitivity fine-tune (the repo's established recalibration
pattern, e.g. narrower sensitivity sweep around 0.3-0.4 instead of
0.3/0.4/0.5, which drove the parameter-sensitivity grid's std up).
