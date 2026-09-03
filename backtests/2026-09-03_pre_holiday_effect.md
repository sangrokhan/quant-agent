# Backtest report: Pre-3-day-weekend / pre-holiday effect

**Strategy file:** `strategies/2026-09-03_pre_holiday_effect.py`
**Hypothesis:** Long from the close of the last trading day before a
calendar gap of >=3 days (weekend adjacent to a holiday closure, or any
3-day weekend) to the next trading day's close, flat otherwise. Source:
Google AI-overview + QuantifiedStrategies.com search snippet for "Do Stocks
Rise Or Drop Before A 3-day Weekend?" -- "Stocks rise before US 3-day
weekends. Pre-holiday returns beat random trading days. Strategy buys
Thursday, sells Friday. Backtest covers S&P 500 since 1960." AI overview:
pre-holiday sessions post above-average returns with low volatility,
attributed to reduced institutional selling/lower liquidity around
holidays.

Implementation detects any calendar gap >=3 days between consecutive
trading-calendar dates in the price series (data-native, no hardcoded
holiday list) rather than only the classic Fri->Mon 3-day weekend --
`min_gap_days` swept at {2,3,4}.

## Grid test (validation/grid_test.py::run_strategy_grid)

`min_gap_days` in {2,3,4} x QQQ/SPY/BTC-USDT/ETH-USDT x 3 vol terciles, 36
cells, 2019-2026:

- **pass_fraction: 0.194** (7/36)
- by_asset_class: equity 7/18, crypto 0/18 (crypto has zero signal -- 24/7
  market, no calendar gaps -- correctly generates 0 nonzero-return days,
  confirming the implementation is asset-class-aware as intended)
- by_vol_regime: low 4/12, mid 3/12, high 0/12
- best_cell: QQQ, min_gap_days=3, low-vol tercile, Sharpe 2.04
- worst_cell: QQQ, min_gap_days=4, low-vol tercile, Sharpe -0.96 (sign flips
  entirely between adjacent parameter values -- a red flag repeated below)

## Standard validators (primary config: QQQ, min_gap_days=3)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.705 | 1.0 |
| max_drawdown | pass | 0.201 | 0.25 |
| transaction_cost_survival | **FAIL** | 0.087 (net Sharpe) | 0.5 |
| parameter_sensitivity | **FAIL** | rel.std 1.379 | 0.5 |
| SPY sharpe (same config) | **FAIL** | 0.504 | 1.0 |
| SPY max_drawdown | pass | 0.233 | 0.25 |

Parameter sensitivity is decisively broken: Sharpe at min_gap_days=2/3/4 on
QQQ swings from roughly flat/negative to 2.04 (best grid cell, low-vol
slice) to negative again -- the effect is not robust to the exact gap
threshold chosen, and the grid's headline "best cell" of 2.04 is a narrow
low-vol-tercile artifact, not representative of the full-sample 0.705.
High turnover (400 trades over 7.7y on daily bars, since virtually every
week has a 2-3 day weekend at min_gap_days=2/3) means transaction costs
erode the edge almost entirely (net Sharpe 0.087).

## Decision: REJECT

Sharpe fails on both QQQ (0.705) and SPY (0.504) at the primary
min_gap_days=3 config, transaction-cost survival fails decisively (net
Sharpe collapses from 0.705 to 0.087 once ~10bps/trade costs are applied to
400 trades), and parameter sensitivity fails outright (rel.std 1.38, more
than double the smallest failure margin seen among other strategies logged
this cron trigger). Crypto trivially rejected (zero signal, as expected for
a 24/7 market with no calendar-gap structure). The pre-holiday drift itself
may be directionally real (consistent with the source's own framing) but
is far too small in magnitude, and far too high-turnover as implemented
here (every ordinary weekend already qualifies at the lowest threshold), to
survive realistic transaction costs on daily-bar QQQ/SPY.
