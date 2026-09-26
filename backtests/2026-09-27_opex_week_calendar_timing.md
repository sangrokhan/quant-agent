# Backtest Report: OPEX (Option-Expiration) Week Calendar Timing

**Strategy file:** `strategies/2026-09-27_opex_week_calendar_timing.py`
**KB entry:** `2026-09-27-001` (rejected)

## Hypothesis

Per [Quantpedia's "Option-Expiration Week Effect"](https://quantpedia.com/strategies/option-expiration-week-effect)
(sourced from Stivers & Sun, SSRN 1571786) and corroborated by
[QuantifiedStrategies.com's OPEX seasonality piece](https://quantifiedstrategies.substack.com/p/the-options-expiration-week-effect-e2a):
large-cap, actively-optioned stocks show abnormally high average weekly
returns during the week containing the monthly 3rd-Friday options
expiration, attributed to option market-maker delta-hedge unwind as
near-term options expire. Rule: go long from the Monday of the 3rd-Friday
week through the 3rd Friday close; flat the rest of the month.

Source's own backtest (S&P 100 universe, 1988-2010): Sharpe 0.61, ~9.3% p.a.,
MDD -15.14%.

## Single-config metrics (hold_extra_days=0, full sample 2018-01 to 2026-09)

| Symbol | Full-sample Sharpe | Total return |
|---|---|---|
| QQQ | 0.013 | +1.1% |
| SPY | -0.268 | -18.8% |

Both decisively below the 1.0 Sharpe threshold.

## Grid test summary (hold_extra_days in {0,1,2} x equity{QQQ,SPY}/crypto{BTC/USDT,ETH/USDT} x 3 vol terciles)

```
total_cells: 36
passed_cells: 0
pass_fraction: 0.0
by_asset_class: equity 0/18, crypto 0/18
by_vol_regime: low 0/12, mid 0/12, high 0/12
best_cell: BTC/USDT, high-vol, hold_extra_days=1, Sharpe=1.006 (single spurious cell, not corroborated elsewhere -- crypto has no OPEX mechanism)
worst_cell: SPY, mid-vol, hold_extra_days=0, Sharpe=-0.629
```

## Validators run

- Sharpe ratio: **FAIL** (all 36 grid cells, both single-symbol full-sample configs)
- Given the decisive 0/36 grid failure and negative-to-flat full-sample
  Sharpe on both equity symbols, no further validators (MDD, walk-forward,
  transaction-cost, parameter-sensitivity) were run -- the primary signal
  metric already falsifies the hypothesis outright.

## Decision: REJECTED

The source's own multi-decade, cross-sectional S&P 100 basket result
(Sharpe 0.61) does not replicate on a single-symbol QQQ/SPY 2018-2026
backtest. Plausible explanations: (a) the effect is genuinely cross-sectional
(driven by aggregate market-maker rebalancing flows across the largest 100
optioned names, not visible in any single index-tracking ETF), (b) the
effect may have decayed/been arbitraged away since the 1988-2010 sample
period, or (c) QQQ/SPY (themselves highly-optioned index ETFs, not
individual large-cap stocks) may not carry the same delta-hedge rebalancing
dynamic as individual constituent stocks. Crypto legs correctly show no
consistent edge (no options-expiration cycle mechanism applies), confirming
feasibility expectations rather than adding real signal.

## Notes for future iterations

If revisiting: consider testing on a cross-sectional basket of individual
S&P 100 constituents (would require extending `data/loaders.py` with a
basket-fetch helper -- a known infrastructure gap already flagged in prior
KB entries e.g. `2026-09-26-075`) rather than a single index ETF, since the
source's own mechanism is explicitly about aggregate hedge-rebalancing
across many optioned single-stocks.
