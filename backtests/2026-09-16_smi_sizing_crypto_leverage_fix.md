# SMI Sizing Dial: Crypto Leverage-Cap Fix (2026-09-16-065)

## Hypothesis
Direct fix for prior id 2026-09-14-098 (Stochastic Momentum Index, William
Blau 1993, close displacement from midpoint of high-low range, numerator and
denominator each double-EMA-smoothed then divided, used as a continuous
sizing dial within an SMA(trend_window) uptrend gate, accepted QQQ-only,
rejected SPY on TC-survival AND rejected crypto BTC/USDT on decisive MDD
30.95%>25%). This sub-iteration applies this repo's standard
leverage-cap-aware retune (leverage_cap cut to 0.25-0.3, base_exposure
reduced, deadband scaled proportionally to 0.08) to the identical unmodified
SMI strategy code (`strategies/2026-09-14_smi_sizing_sma_trend.py`) for
crypto only. No new external research this sub-iteration.

## Grid summary (Step 6, crypto only, leverage-capped)
`param_grid={smi_range_window:[13,20], smi_sensitivity:[0.4,0.6], base_exposure:[0.15,0.2]}`,
fixed leverage_cap=0.3/deadband=0.08, symbols crypto {BTC/USDT, ETH/USDT},
vol_regime_splits=3.

- total_cells: 48, passed_cells: 35, pass_fraction: 0.729
- by_vol_regime: low 11/16, mid 16/16, high 8/16
- best_cell: ETH/USDT, smi_range_window=13/smi_sensitivity=0.4/base_exposure=0.2, mid-vol Sharpe 2.560

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.423 | 0.144 | 0.958 | 1.00 | 0.018 | Yes |
| ETH/USDT | 1.191 | 0.163 | 0.858 | 1.00 | 0.025 | Yes |

Configs:
- BTC/USDT: smi_range_window=13, smi_sensitivity=0.4, base_exposure=0.2, deadband=0.08, leverage_cap=0.3
- ETH/USDT: smi_range_window=13, smi_sensitivity=0.4, base_exposure=0.2, deadband=0.08, leverage_cap=0.25

## Outcome
Accepted (crypto, this sub-iteration) -- both BTC/USDT and ETH/USDT now pass
all 5 validators, rescuing the prior 2026-09-14-098 crypto MDD rejection.
Combined with the existing QQQ-only accept from 2026-09-14-098, SMI's
continuous-sizing dial now covers equity QQQ + full crypto (SPY remains
separately rejected on its own TC-survival grounds).

Fifth confirmation this cron trigger of the leverage-cap-aware retune
pattern with proportionally-scaled deadband reliably rescuing crypto
MDD-driven rejections (after TMF/PVO earlier, R2/TSI/RMI this trigger).

Source: no new URL fetched -- SMI formula already documented in this repo
from 2026-09-14-098 (luxalgo.com, tradiecapital.com, forexmt4indicators.com,
ta-lib.org).
