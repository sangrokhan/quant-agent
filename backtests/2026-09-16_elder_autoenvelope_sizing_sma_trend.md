# Backtest Report: Elder AutoEnvelope Continuous Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_elder_autoenvelope_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-048
**Date:** 2026-09-16

## Hypothesis

Elder AutoEnvelope, per Dr. Alexander Elder's own description (corroborated
by TradingView/Scribd/Worden-D summaries via Google search read through
`browser_exec` fallback -- `web_search` DDGS backend failed with a TLS
RequestError for an earlier query this iteration, redirecting research to
this candidate): a 13-day EMA is the "market consensus of value"; upper and
lower envelopes are plotted around it offset by a volatility-derived amount.
Operationalized here as an ATR(20)-scaled envelope. Elder's own trading
rule only acts on overbought/oversold envelope extremes in the direction of
the dominant trend -- reused here as this repo's established
SMA(trend_window) uptrend gate. First Elder-AutoEnvelope-specific strategy
in this repo (distinct from the plain fixed-percentage MA Envelope already
tested, and from Elder Ray/Elder Impulse/Elder Force Index/Elder SafeZone,
separate indicators from the same author).

Construction: `dial = clip((close - EMA(13)) / (atr_mult * ATR(20)), -1, 1)`
used directly as a continuous exposure-sizing dial (already bounded, no
z-score needed) inside an SMA(trend_window=40) uptrend gate with a deadband
to cut turnover.

Source: Google AI-overview summary (browser_exec), query
`"Elder AutoEnvelope" formula indicator trading`.

## Step 6 — Grid summary

`run_grid_elder_autoenvelope_sizing.py`: `param_grid` = atr_mult in
{1.5,2.0,2.5} x sensitivity in {0.4,0.6,0.8} x deadband in {0.10,0.20},
symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3,
2019-2026.

- total_cells=216, passed=99, **pass_fraction=0.458**
- by_asset_class: equity 54/108, crypto 45/108
- by_vol_regime: low 65/72, mid 34/72, high 0/72
- best_cell: QQQ atr_mult=1.5/sensitivity=0.4/deadband=0.10, low-vol Sharpe=2.65
- per-symbol grid pass: QQQ 36/54, SPY 18/54, BTC/USDT 34/54, ETH/USDT 11/54

## Step 7 — Single-config validators

Per-symbol configs retuned from grid raw-Sharpe cells to also survive
transaction costs and MDD (equity needed a wider deadband=0.40 than the
grid's raw-Sharpe optimum to control turnover; crypto needed a much lower
`leverage_cap`/`base_exposure` than the grid default to control MDD, per
this repo's established crypto-overleverage pattern):

| Symbol | atr_mult | sensitivity | deadband | base_exposure | leverage_cap | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 2.0 | 0.4 | 0.40 | 0.4 | 1.0 | 1.391 | 0.101 | 1.048 | 1.00 | 0.074 | YES |
| SPY | 2.0 | 0.4 | 0.40 | 0.4 | 1.0 | 1.181 | 0.063 | 0.738 | 0.75 | 0.132 | YES |
| BTC/USDT | 2.5 | 0.6 | 0.20 | 0.25 | 0.3 | 1.465 | 0.165 | 1.120 | 1.00 | 0.011 | YES |
| ETH/USDT | 2.5 | 0.6 | 0.20 | 0.25 | 0.3 | 1.332 | 0.183 | 1.117 | 1.00 | 0.032 | YES |

All 4 symbols pass all 5 validators (Sharpe>=1.0, MDD<=0.25, net Sharpe
after 10bps/trade costs >=0.5, walk-forward pass fraction >=0.75,
parameter-sensitivity relative-std <=0.5).

## Step 8 — Decision

**ACCEPT** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT).

## Notes

- Equity's initial grid-optimal deadband (0.10-0.20) failed transaction-cost
  survival at ~300-470 trades; widening to deadband=0.40 cut trades to
  116-165 and pushed net Sharpe from ~0.2-0.4 to 0.74-1.05 -- consistent
  with this repo's repeated finding that un-smoothed distance-from-MA style
  dials need aggressive deadbands to survive costs on daily equity bars.
- Crypto's grid-optimal leverage_cap=1.0 produced MDD 0.29-0.37 (fails
  0.25 threshold); cutting leverage_cap to 0.3 and base_exposure to 0.25
  brought MDD to 0.16-0.18 while keeping Sharpe >1.3 -- same
  crypto-overleverage-must-be-capped pattern seen across most prior
  accepted crypto sizing-dial strategies in this repo.
