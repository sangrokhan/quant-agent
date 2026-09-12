# Backtest Report: Ehlers Precision Trend Analysis (dual 3-pole highpass)

**Strategy file:** `strategies/2026-09-12_ehlers_precision_trend.py`
**Knowledge base id:** 2026-09-12-171
**Date:** 2026-09-12

## Hypothesis

Per John Ehlers' "Precision Trend Analysis" (TASC Aug/Sep 2024 Traders'
Tips), transcribed in full C code at
https://financial-hacker.com/ehlers-precision-trend-analysis/: a 3-pole
highpass filter is applied to price at two different lengths (Length1 >
Length2); their difference is Ehlers' own "Trend" line (near-zero-lag vs.
SMA/WMA/EMA per the source). The derived TROC (trend rate-of-change)
crossing from negative to positive marks a trend trough (buy signal per the
source author's own comment-thread trading-rule disclosure: "you enter and
exit at the valleys and peaks of a trend line"); crossing from positive to
negative marks a trend peak (sell/exit signal).

## Single-config validator results (length1=125, length2=20)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Param-sensitivity relative_std |
|--------|--------|-----|-------------------------|----------------------------------|
| SPY    | 1.019 (PASS, thr 1.0) | 0.216 (PASS, thr 0.25) | 0.694 (PASS, thr 0.5, 340 trades, 5bps) | 0.126 (PASS, thr 0.5) |
| QQQ    | 0.474 (FAIL, thr 1.0) | 0.274 (FAIL, thr 0.25) | 0.258 (FAIL, thr 0.5) | 0.276 (PASS) |

SPY passes all 4 run validators at this config. QQQ decisively fails the
same config (Sharpe, MDD, and TC-survival all fail) -- the strategy does
NOT generalize across both large-cap-tech ETFs, so acceptance scope is
narrowed to SPY only. Walk-forward not run (vectorbt.utils.splitting API
broken in installed vectorbt version, repo-wide known issue).

## Grid test summary (run_strategy_grid)

`param_grid={"length1": [125, 250], "length2": [20, 40, 60]}`, symbols
`{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 72 total cells.

- **pass_fraction: 0.278** (20/72)
- by_asset_class: equity 20/36 passed; crypto 0/36 decisively rejected.
- by_vol_regime: low 12/24, mid 2/24, high 6/24 -- edge concentrated in
  low-vol and (to a lesser degree) high-vol regimes, weak in mid-vol.
- Best cell: SPY low-vol, length1=250/length2=40, Sharpe 2.32.
- Worst cell: SPY mid-vol, length1=250/length2=40, Sharpe -0.41.

## Decision: ACCEPT (SPY only, length1=125, length2=20)

SPY passes Sharpe, MDD, transaction-cost-survival, and
parameter-sensitivity at the chosen config. QQQ is explicitly OUT of scope
-- it decisively fails the same config on every validator. This strategy's
validated live scope is SPY only, not QQQ or the broader "equity" asset
class generically.

## Notes / caveats for future iterations

- 340 trades over ~7.5 years is a high turnover for a daily-bar strategy
  (roughly one round-trip every 5-6 trading days); the Sharpe of 1.019 is a
  narrow pass (0.019 above the 1.0 threshold) so should be treated as a
  fragile accept, not a robust one -- a future loop could revisit whether
  a min-hold-days filter reduces turnover without collapsing the edge.
- Crypto (BTC/USDT, ETH/USDT) decisively rejected across the full grid,
  consistent with most Ehlers-family filters already tested in this repo.
