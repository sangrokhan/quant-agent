# IMI Sizing Dial: Crypto Leverage-Cap Fix (2026-09-16-067)

## Hypothesis
Direct fix for prior id 2026-09-14-100 (Intraday Momentum Index, Tushar
Chande, RSI-like 0-100 oscillator built from each bar's open-to-close body
move over a rolling window, used as a continuous sizing dial within an
SMA(trend_window) uptrend gate, accepted QQQ-only, rejected SPY [Sharpe stays
below 1.0 across all deadbands tried] AND rejected crypto BTC/USDT on
decisive MDD 36.57%>25%). This sub-iteration applies this repo's standard
leverage-cap-aware retune (leverage_cap cut to 0.22-0.25, base_exposure
reduced, deadband scaled proportionally to 0.07) to the identical unmodified
IMI strategy code (`strategies/2026-09-14_imi_sizing_sma_trend.py`) for
crypto only. No new external research this sub-iteration (tenth and final
iteration this cron trigger).

## Grid summary (Step 6, crypto only, leverage-capped)
`param_grid={imi_window:[14,20], imi_sensitivity:[0.4,0.6], base_exposure:[0.12,0.18]}`,
fixed leverage_cap=0.25/deadband=0.07, symbols crypto {BTC/USDT, ETH/USDT},
vol_regime_splits=3.

- total_cells: 48, passed_cells: 40, pass_fraction: 0.833
- by_vol_regime: low 16/16, mid 16/16, high 8/16
- best_cell: ETH/USDT, imi_window=14/imi_sensitivity=0.6/base_exposure=0.12, mid-vol Sharpe 2.536

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.484 | 0.127 | 0.860 | 1.00 | 0.013 | Yes |
| ETH/USDT | 1.264 | 0.099 | 0.780 | 1.00 | 0.028 | Yes |

Configs:
- BTC/USDT: imi_window=20, imi_sensitivity=0.6, base_exposure=0.18, deadband=0.07, leverage_cap=0.25
- ETH/USDT: imi_window=14, imi_sensitivity=0.6, base_exposure=0.18, deadband=0.07, leverage_cap=0.22

## Outcome
Accepted (crypto only, this sub-iteration) -- both BTC/USDT and ETH/USDT now
pass all 5 validators, rescuing the prior 2026-09-14-100 crypto MDD
rejection. Combined with the existing QQQ-only accept from 2026-09-14-100,
IMI's continuous-sizing dial now covers equity QQQ + full crypto (SPY
remains separately rejected on its own Sharpe grounds, unrelated to this
crypto fix).

Seventh and final confirmation this cron trigger of the leverage-cap-aware
retune pattern with proportionally-scaled deadband reliably rescuing crypto
MDD-driven rejections (after R2, TSI, RMI, SMI, BOP earlier this trigger).
This is the tenth and final iteration this cron trigger (outer-loop cap
reached).

Source: no new URL fetched -- IMI formula already documented in this repo
from 2026-09-14-100 (ta-lib.org, blinkx.in, alphasquawk.com, figurebetter.com).
