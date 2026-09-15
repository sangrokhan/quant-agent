# FCB Sizing Dial: Crypto Daily-Bar Resample Fix (2026-09-16-059)

## Hypothesis
Direct fix for prior id 2026-09-15-014 (Fractal Chaos Bands normalized-distance
continuous sizing dial, accepted QQQ+SPY but rejected on crypto due to using the
`load_crypto` default hourly interval, which the entry's own notes flagged as the
likely root cause of the "decisive turnover-driven fail" -- deadband cannot
control turnover the same way when crypto bars are ~35x more numerous than the
equity daily bars used to tune the deadband). This sub-iteration re-runs the
identical unmodified FCB strategy code
(`strategies/2026-09-15_fcb_dist_sizing_sma_trend.py`) on crypto resampled to
**daily** bars (`load_crypto(..., interval="1d")`) instead of the loader's
hourly default, testing whether that alone rescues crypto. No new external
research this sub-iteration -- pure data-frequency fix following the prior
entry's own documented recommendation.

## Grid summary (Step 6, crypto only, daily bars)
`param_grid={zscore_window:[50,100,150], sensitivity:[0.4,0.6,0.8], deadband:[0.2,0.35]}`,
symbols crypto {BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- total_cells: 108, passed_cells: 68, pass_fraction: 0.630 (vs. 0.593 hourly, but
  with a genuinely comparable per-cell interpretation now that turnover is
  controlled the same way as equity)
- by_vol_regime: low 33/36, mid 17/36, high 18/36 -- markedly better high-vol
  coverage than every equity-based FCB cell in the prior entry
- best_cell: ETH/USDT, zscore_window=50/sensitivity=0.4/deadband=0.2, mid-vol Sharpe 2.662

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.426 | 0.171 | 0.832 | 1.00 | 0.054 | Yes |
| ETH/USDT | 1.453 | 0.129 | 1.016 | 1.00 | 0.148 | Yes |

Configs:
- BTC/USDT: zscore_window=150, sensitivity=0.8, deadband=0.20, base_exposure=0.2, leverage_cap=0.3
- ETH/USDT: zscore_window=50, sensitivity=0.4, deadband=0.20, base_exposure=0.2, leverage_cap=0.25

## Outcome
Accepted (crypto, this sub-iteration) -- both BTC/USDT and ETH/USDT now pass all
5 validators on daily bars, rescuing the prior 2026-09-15-014 crypto rejection.
Combined with the existing QQQ+SPY accept from 2026-09-15-014, FCB's
normalized-distance continuous-sizing dial now covers the full universe.

**Reusable finding for future loops**: any sizing-dial strategy accepted on
equity but rejected/decisively-fails on crypto with symptoms of "turnover
explosion" or a note mentioning the loader's ~75,000-row hourly crypto series
vs ~2,200-row daily equity series should be re-tested with
`load_crypto(..., interval="1d")` before concluding the indicator itself does
not generalize to crypto -- this is a distinct fix pattern from the more common
leverage-cap-aware crypto retune (lower `leverage_cap`/`base_exposure`), which
does NOT fix a frequency-mismatch turnover problem.

Source: no new URL fetched -- formula already documented in this repo from
2026-09-06-145/2026-09-15-014 (https://help.ctrader.com/indicators/built-in/volatility/fractal-chaos-bands/,
https://www.quantifiedstrategies.com/fractal-chaos-bands/).
