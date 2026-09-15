# TSI Sizing Dial: Crypto Leverage-Cap Fix (2026-09-16-063)

## Hypothesis
Direct fix for prior id 2026-09-14-096 (True Strength Index, William Blau
1991, TSI=100*EMA(EMA(price_diff,slow),fast)/EMA(EMA(|price_diff|,slow),fast),
used as a continuous sizing dial within an SMA(trend_window) uptrend gate,
accepted QQQ+SPY but decisively rejected on crypto BTC/USDT due to MDD
31.17%>25% despite strong Sharpe/TC/WF/param-sensitivity). This sub-iteration
applies this repo's standard leverage-cap-aware retune (leverage_cap cut to
0.3-0.35, base_exposure reduced, deadband scaled down to 0.08 per the
proportional-scaling caution discovered in 2026-09-16-062) to the identical
unmodified TSI strategy code (`strategies/2026-09-14_tsi_sizing_sma_trend.py`).
No new external research this sub-iteration.

## Grid summary (Step 6, crypto only, leverage-capped)
`param_grid={tsi_fast:[13,20], tsi_sensitivity:[0.4,0.6], base_exposure:[0.15,0.25]}`,
fixed leverage_cap=0.35/deadband=0.08, symbols crypto {BTC/USDT, ETH/USDT},
vol_regime_splits=3.

- total_cells: 48, passed_cells: 40, pass_fraction: 0.833
- by_vol_regime: low 16/16, mid 16/16, high 8/16
- best_cell: ETH/USDT, tsi_fast=13/tsi_sensitivity=0.6/base_exposure=0.25, mid-vol Sharpe 2.540

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.473 | 0.165 | 1.123 | 1.00 | 0.009 | Yes |
| ETH/USDT | 1.176 | 0.209 | 0.925 | 1.00 | 0.011 | Yes |

Configs:
- BTC/USDT: tsi_fast=13, tsi_sensitivity=0.4, base_exposure=0.25, deadband=0.08, leverage_cap=0.35
- ETH/USDT: tsi_fast=13, tsi_sensitivity=0.6, base_exposure=0.25, deadband=0.08, leverage_cap=0.30

## Outcome
Accepted (crypto, this sub-iteration) -- both BTC/USDT and ETH/USDT now pass
all 5 validators, rescuing the prior 2026-09-14-096 crypto MDD rejection.
Combined with the existing QQQ+SPY accept from 2026-09-14-096, TSI's
continuous-sizing dial now covers the full universe.

Source: no new URL fetched -- TSI formula already documented in this repo
from 2026-09-14-096 (nexusfi.com, trendsandbreakouts.com, TA-Lib github
issue#360).
