# R² Sizing Dial: Crypto Leverage-Cap Fix (2026-09-16-062)

## Hypothesis
Direct fix for prior id 2026-09-14-113 (R-squared, coefficient of
determination of a rolling linear regression of price vs. time, used as an
unsigned CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate,
accepted QQQ+SPY but decisively rejected on crypto due to MDD 39.0%>25% at
default leverage_cap=1.0). This sub-iteration applies this repo's
now-standard leverage-cap-aware retune (cut leverage_cap to 0.25-0.3 and
scale base_exposure/deadband accordingly for crypto) to the identical
unmodified R² strategy code (`strategies/2026-09-14_r2_sizing_sma_trend.py`),
testing whether the crypto rejection was purely a leverage/sizing artifact.
No new external research this sub-iteration.

**Implementation note**: the first grid attempt at leverage_cap=0.3 with the
strategy's default deadband=0.30 produced 0 trades on every cell (a
degenerate all-zero-exposure signal) because the deadband exceeded the
entire achievable [0, leverage_cap] exposure range once leverage_cap was cut.
Reducing deadband to 0.10 (proportional to the smaller leverage_cap) fixed
this -- a useful general caution for any leverage-cap retune: deadband must
scale down with leverage_cap, not stay fixed at the equity-tuned value.

## Grid summary (Step 6, crypto only, leverage-capped)
`param_grid={r2_window:[20,30], r2_sensitivity:[0.4,0.6], base_exposure:[0.15,0.2]}`,
fixed leverage_cap=0.3/deadband=0.10, symbols crypto {BTC/USDT, ETH/USDT},
vol_regime_splits=3.

- total_cells: 48, passed_cells: 40, pass_fraction: 0.833
- by_vol_regime: low 16/16, mid 16/16, high 8/16
- best_cell: ETH/USDT, r2_window=20/r2_sensitivity=0.6/base_exposure=0.2, mid-vol Sharpe 2.542

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.428 | 0.148 | 0.903 | 1.00 | 0.041 | Yes |
| ETH/USDT | 1.283 | 0.173 | 1.040 | 1.00 | 0.008 | Yes |

Configs:
- BTC/USDT: r2_window=20, r2_sensitivity=0.4, base_exposure=0.15, deadband=0.10, leverage_cap=0.3
- ETH/USDT: r2_window=20, r2_sensitivity=0.6, base_exposure=0.2, deadband=0.10, leverage_cap=0.25

## Outcome
Accepted (crypto, this sub-iteration) -- both BTC/USDT and ETH/USDT now pass
all 5 validators, rescuing the prior 2026-09-14-113 crypto rejection.
Combined with the existing QQQ+SPY accept from 2026-09-14-113, R²'s
continuous-sizing dial now covers the full universe.

Source: no new URL fetched -- R² formula already documented in this repo
from 2026-09-07-004/2026-09-14-113.
