# Backtest Report: Polynomial Regression Channel Mean Reversion

**Date:** 2026-09-16 (iteration 5, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-16_poly_regression_channel_meanrev.py`

## Hypothesis

Per a Google AI-overview summary of TradingView/Medium/PyQuantLab writeups
on polynomial regression channels: fit a causal rolling degree-2
(quadratic) polynomial trend curve to close price, band it at
`band_std_mult` residual standard deviations. Source's mean-reversion
rule: long when price touches/dips below the lower band AND the channel's
local slope is flat or turning upward (avoid fading a still-falling
channel); exit at the midline (fitted curve value). First polynomial
regression channel strategy in this repo (0 prior matches) — distinct from
10+ prior LINEAR regression channel entries (degree-1) since a quadratic
fit captures curvature/acceleration a straight line cannot, and from
Bollinger Bands (which band a moving average, not a fitted regression
curve).

Source read via `browser_exec` fallback after `web_search`'s DDGS backend
continued failing with the same Yahoo/TLS RequestError seen all iterations
this trigger.

## Grid test summary (Step 6)

`param_grid={channel_window: [30,40,50], band_std_mult: [1.25,1.5,1.75]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`.

- total_cells: 108, passed_cells: 24, **pass_fraction: 0.222**
- by_asset_class: equity 22/54, crypto 2/54
- by_vol_regime: low 19/36, mid 5/36, high 0/36
- best_cell: equity/SPY/low-vol, sharpe 2.29 (channel_window=30,
  band_std_mult=1.25)
- worst_cell: equity/SPY/high-vol, sharpe -0.39

Best full-grid config: `channel_window=30, band_std_mult=1.75` (4/6 equity
grid cells passing, highest among tested combos).

## Single-config validator results (Step 7)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Overall |
|---|---|---|---|---|---|---|
| QQQ | 0.702 (fail, near-miss) | 0.174 (pass) | 0.524 (pass) | 0.75 (pass) | 0.159 rel-std (pass) | REJECT |
| SPY | 0.715 (fail, near-miss) | 0.126 (pass) | 0.488 (fail, near-miss) | 1.00 (pass) | 0.244 rel-std (pass) | REJECT |
| BTC/USDT | 0.258 (fail) | 0.390 (fail) | 0.191 (fail) | 0.75 (pass) | 0.462 rel-std (pass) | REJECT |

## Decision

**Reject across all 3 symbols.** Full-sample Sharpe is a near-miss decisive
fail on both QQQ (0.70) and SPY (0.71), and crypto fails everything
decisively. As with several other strategies tested this trigger, the
grid's apparent low-vol-tercile edge (Sharpe up to 2.29) does not survive
full-sample validation — the edge is regime-concentrated and dilutes to
below the 1.0 bar when averaged across the whole 2019-2026 sample including
2020/2022 stress periods. Strategy file and this report kept as the record
of a rejected attempt.
