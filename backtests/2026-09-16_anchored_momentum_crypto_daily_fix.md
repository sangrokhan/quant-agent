# Anchored Momentum Sizing Dial: Crypto Daily-Bar Resample Fix (2026-09-16-060)

## Hypothesis
Direct fix for prior id 2026-09-15-017 (Anchored Momentum continuous sizing
dial, accepted QQQ+SPY but rejected on crypto due to "decisive turnover-driven
fail on hourly crypto bars" -- same root cause diagnosed and fixed for FCB
earlier this cron trigger, 2026-09-16-059). This sub-iteration re-runs the
identical unmodified Anchored Momentum strategy code
(`strategies/2026-09-15_anchored_momentum_sizing_sma_trend.py`) on crypto
loaded via `load_crypto(..., interval="1d")` instead of the loader's hourly
default. No new external research this sub-iteration.

## Grid summary (Step 6, crypto only, daily bars)
`param_grid={ema_period:[6,10], sma_period:[8,20], sensitivity:[0.4,0.6,0.8], deadband:[0.2,0.35]}`,
symbols crypto {BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- total_cells: 144, passed_cells: 79, pass_fraction: 0.549
- by_vol_regime: low 45/48, mid 20/48, high 14/48
- best_cell: ETH/USDT, ema_period=6/sma_period=8/sensitivity=0.6/deadband=0.35, mid-vol Sharpe 2.621

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.506 | 0.057 | 0.707 | 1.00 | 0.064 | Yes |
| ETH/USDT | 1.310 | 0.117 | 1.111 | 1.00 | 0.031 | Yes |

Configs:
- BTC/USDT: ema_period=10, sma_period=8, sensitivity=0.6, deadband=0.20, base_exposure=0.2, leverage_cap=0.3
- ETH/USDT: ema_period=10, sma_period=20, sensitivity=0.8, deadband=0.20, base_exposure=0.2, leverage_cap=0.25

Note: the grid's nominal tercile-average best-cell for ETH (deadband=0.35)
produced a degenerate full-sample result (0 trades, Sharpe=Infinity) when
checked against the full sample -- picked the next-best non-degenerate
config instead. This is a reminder that grid tercile averages can mask
degenerate full-sample edge cases; always sanity-check the chosen config's
full-sample trade count before finalizing.

## Outcome
Accepted (crypto, this sub-iteration) -- both BTC/USDT and ETH/USDT now pass
all 5 validators on daily bars, rescuing the prior 2026-09-15-017 crypto
rejection. Combined with the existing QQQ+SPY accept from 2026-09-15-017,
Anchored Momentum's continuous-sizing dial now covers the full universe.

This confirms the crypto-daily-bar-resample fix pattern (first established
for FCB, 2026-09-16-059) generalizes to a second sizing-dial strategy that
shares the same root cause (turnover-driven rejection on hourly bars).

Source: no new URL fetched -- formula already documented in this repo from
2026-09-06-177/2026-09-15-017 (https://doc.stocksharp.com/api-examples/1944_AnchoredMomentum.html).
