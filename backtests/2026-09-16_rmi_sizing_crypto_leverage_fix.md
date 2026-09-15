# RMI Sizing Dial: Crypto Leverage-Cap Fix (2026-09-16-064)

## Hypothesis
Direct fix for prior id 2026-09-14-097 (Relative Momentum Index, Roger Altman
1993, RSI Wilder-smoothing applied to N-bar momentum step, used as a
continuous sizing dial within an SMA(trend_window) uptrend gate, accepted
QQQ-only, rejected SPY on Sharpe+TC-survival AND rejected crypto BTC/USDT on
decisive MDD 34.70%>25%). This sub-iteration applies this repo's standard
leverage-cap-aware retune (leverage_cap cut to 0.25-0.3, base_exposure
reduced, deadband scaled proportionally to 0.08) to the identical unmodified
RMI strategy code (`strategies/2026-09-14_rmi_sizing_sma_trend.py`) for
crypto only. No new external research this sub-iteration.

## Grid summary (Step 6, crypto only, leverage-capped)
`param_grid={momentum_period:[5,10], rmi_sensitivity:[0.4,0.6], base_exposure:[0.15,0.2]}`,
fixed leverage_cap=0.3/deadband=0.08, symbols crypto {BTC/USDT, ETH/USDT},
vol_regime_splits=3.

- total_cells: 48, passed_cells: 39, pass_fraction: 0.8125
- by_vol_regime: low 15/16, mid 16/16, high 8/16
- best_cell: ETH/USDT, momentum_period=10/rmi_sensitivity=0.4/base_exposure=0.2, mid-vol Sharpe 2.517

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.480 | 0.149 | 1.005 | 1.00 | 0.039 | Yes |
| ETH/USDT | 1.304 | 0.170 | 0.977 | 1.00 | 0.063 | Yes |

Configs:
- BTC/USDT: momentum_period=5, rmi_sensitivity=0.4, base_exposure=0.2, deadband=0.08, leverage_cap=0.3
- ETH/USDT: momentum_period=5, rmi_sensitivity=0.4, base_exposure=0.2, deadband=0.08, leverage_cap=0.25

## Outcome
Accepted (crypto, this sub-iteration) -- both BTC/USDT and ETH/USDT now pass
all 5 validators, rescuing the prior 2026-09-14-097 crypto MDD rejection.
Combined with the existing QQQ-only accept from 2026-09-14-097, RMI's
continuous-sizing dial now covers equity QQQ + full crypto (SPY remains
separately rejected on its own Sharpe/TC-survival grounds, unrelated to this
crypto fix).

Fourth confirmation this cron trigger of the leverage-cap-aware retune
pattern (after TMF/PVO earlier and R2/TSI this trigger) reliably rescuing
crypto MDD-driven rejections when deadband is scaled down proportionally
with leverage_cap.

Source: no new URL fetched -- RMI formula already documented in this repo
from 2026-09-14-097 (everycalculators.com, luxalgo.com, onetradejournal.com,
quantstrategy.io).
