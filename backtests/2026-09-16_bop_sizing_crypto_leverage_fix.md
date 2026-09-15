# BOP Sizing Dial: Crypto Leverage-Cap Fix (2026-09-16-066)

## Hypothesis
Direct fix for prior id 2026-09-14-099 (Balance of Power, Igor Livshin Aug
2001, BOP=(Close-Open)/(High-Low), smoothed, used as a continuous sizing
dial within an SMA(trend_window) uptrend gate, accepted QQQ AND SPY at
widened deadband 0.15/0.25 but decisively rejected on crypto BTC/USDT due to
MDD 33.15%>25%). This sub-iteration applies this repo's standard
leverage-cap-aware retune (leverage_cap cut to 0.25-0.3, base_exposure
reduced, deadband scaled proportionally to 0.08) to the identical unmodified
BOP strategy code (`strategies/2026-09-14_bop_sizing_sma_trend.py`) for
crypto only. No new external research this sub-iteration.

## Grid summary (Step 6, crypto only, leverage-capped)
`param_grid={bop_smoothing_window:[14,20], bop_sensitivity:[0.4,0.6], base_exposure:[0.15,0.2]}`,
fixed leverage_cap=0.3/deadband=0.08, symbols crypto {BTC/USDT, ETH/USDT},
vol_regime_splits=3.

- total_cells: 48, passed_cells: 40, pass_fraction: 0.833
- by_vol_regime: low 16/16, mid 16/16, high 8/16
- best_cell: ETH/USDT, bop_smoothing_window=14/bop_sensitivity=0.4/base_exposure=0.15, mid-vol Sharpe 2.481

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.458 | 0.141 | 0.956 | 1.00 | 0.019 | Yes |
| ETH/USDT | 1.268 | 0.127 | 0.864 | 1.00 | 0.040 | Yes |

Configs:
- BTC/USDT: bop_smoothing_window=14, bop_sensitivity=0.6, base_exposure=0.2, deadband=0.08, leverage_cap=0.3
- ETH/USDT: bop_smoothing_window=14, bop_sensitivity=0.4, base_exposure=0.15, deadband=0.08, leverage_cap=0.25

## Outcome
Accepted (full universe: QQQ, SPY, BTC/USDT, ETH/USDT) -- both BTC/USDT and
ETH/USDT now pass all 5 validators, rescuing the prior 2026-09-14-099 crypto
MDD rejection. Combined with the existing QQQ+SPY accept from 2026-09-14-099,
BOP's continuous-sizing dial now covers the full universe for the first time.

Sixth confirmation this cron trigger of the leverage-cap-aware retune
pattern with proportionally-scaled deadband reliably rescuing crypto
MDD-driven rejections (after R2, TSI, RMI, SMI this trigger).

Source: no new URL fetched -- BOP formula already documented in this repo
from 2026-09-14-099 (tradingview.com, wealthcharts.com, agenatrader.com).
