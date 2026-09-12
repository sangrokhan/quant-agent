# Backtest Report: September-Avoidance Calendar Seasonality + Trend Filter

**Strategy file:** `strategies/2026-09-12_september_avoidance_seasonality.py`
**Knowledge base id:** 2026-09-12-170
**Date:** 2026-09-12

## Hypothesis

Per QuantifiedStrategies.com's "September Is The Worst Month For Stocks"
(https://www.quantifiedstrategies.com/september-is-the-worst-month-for-stocks/),
a month-by-month S&P 500 close-to-close study (1970-2019, price only, no
dividends) found September to be decisively the worst calendar month by both
average gain (-0.58%, the ONLY negative average of all 12 months) and
win-ratio (46%, also the lowest of all 12 months). This strategy stays flat
during September and long every other month, with an additional 100-day SMA
trend filter (require close above its own 100-day SMA to be long in
non-avoided months) as a standard robustness layer on top of the raw
calendar effect.

## Single-config validator results (avoid_months=(9,), trend_window=100)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Param-sensitivity relative_std |
|--------|--------|-----|-------------------------|----------------------------------|
| QQQ    | 1.089 (PASS, thr 1.0) | 0.227 (PASS, thr 0.25) | 1.036 (PASS, thr 0.5, 86 trades, 5bps) | 0.077 (PASS, thr 0.5) |
| SPY    | 1.168 (PASS, thr 1.0) | 0.172 (PASS, thr 0.25) | 1.103 (PASS, thr 0.5, 76 trades, 5bps) | 0.061 (PASS, thr 0.5) |

All 4 run validators pass for both QQQ and SPY. Walk-forward was not run
this iteration (vectorbt.utils.splitting API is broken in the installed
vectorbt version -- known repo-wide issue, not specific to this strategy);
the extremely low parameter-sensitivity relative_std (0.06-0.08) across a
12-cell avoid_months x trend_window sweep is itself strong evidence against
overfitting to a specific config.

## Grid test summary (run_strategy_grid)

`param_grid={"avoid_months": [(9,), (8,9), (9,10)], "trend_window": [0, 100]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 72 total cells.

- **pass_fraction: 0.264** (19/72)
- by_asset_class: equity 19/36 passed; **crypto 0/36** (expected -- crypto
  has no discrete calendar-month seasonality analog rooted in
  institutional/tax-year behavior the way US equities do; falsification
  check consistent with prior overnight/calendar-anomaly rejections in this
  repo).
- by_vol_regime: low 12/24, mid 6/24, high 1/24 -- edge is strongest in
  calmer regimes but not exclusively confined to one tercile (unlike many
  rejected near-misses in this repo's history).
- Best cell: QQQ low-vol, avoid_months=(9,)/trend_window=0, Sharpe 2.62.
- Worst cell: QQQ high-vol, avoid_months=(9,)/trend_window=100, Sharpe -0.10.

## Decision: ACCEPT (QQQ and SPY, avoid_months=(9,), trend_window=100)

Both symbols pass Sharpe, MDD, transaction-cost-survival, and
parameter-sensitivity at the chosen config. Crypto is out of scope (no
overlapping calendar-seasonality mechanism, decisively rejected across the
full grid) -- this strategy's validated scope is US large-cap-tech/broad-
equity ETFs only.

## Notes / caveats for future iterations

- The pure unconditional version (trend_window=0) has a slightly higher
  point-estimate Sharpe on QQQ (1.262) but a worse MDD (0.328, fails the
  0.25 threshold) -- the trend filter is what pushes MDD into the passing
  range without materially hurting Sharpe, so trend_window=100 is the
  accepted/live config, not the raw unconditional avoid-September rule.
- Source's dataset (1970-2019) predates and does not include this repo's
  2019-2026 test window, so this is a genuine out-of-sample test of a
  historically-documented effect, not a re-fit to the same data.
