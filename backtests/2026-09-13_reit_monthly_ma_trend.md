# Backtest Report: Monthly-Evaluated MA Trend, REIT-sector (XLRE/IYR)

**Hypothesis:** Monthly-decision moving-average trend-following on REIT
sector proxies. Source: Quantpedia blog "Anomaly-Based Trading Strategies
in the Real Estate Sector. Can the Market Be Beaten?" (Sona Beluska, 16
March 2026,
https://quantpedia.com/anomaly-based-trading-strategies-in-the-real-estate-sector-can-the-market-be-beaten/).
The source tested the RlEst Fama-French real-estate industry index
(monthly data, 1926-2025): at month-end compare close to an N-month SMA
(N=3..12), invest next month if above, else hold cash. All tested N
outperformed RlEst buy-and-hold but underperformed the broader 12-industry
market benchmark.

**Adaptation:** Daily-bar approximation using XLRE/IYR (equity REIT-sector
ETFs) plus BTC/USDT, ETH/USDT (crypto, for the repo's required asset-class
breadth split -- crypto obviously isn't REIT-related, testing only the
generic mechanism). `eval_frequency_days=21` approximates monthly
re-decision; `ma_window` in trading days (63/126/252 ~= 3/6/12 months).

## Grid summary (Step 6)

`ma_window in [63, 126, 252]` x `eval_frequency_days=[21]` x
`{XLRE, IYR}` (equity) x `{BTC/USDT, ETH/USDT}` (crypto) x 3 vol terciles
= 36 cells, 2016-01-01 to 2026-09-01.

- **pass_fraction: 0/36 (0.0)**
- by_asset_class: equity 0/18, crypto 0/18
- by_vol_regime: low 0/12, mid 0/12, high 0/12
- best_cell: ma_window=252, XLRE, low-vol regime, Sharpe 0.637 (still
  below the 1.0 threshold)
- worst_cell: ma_window=63, XLRE, high-vol regime, Sharpe -0.879

## Single-config validation (Step 7), best full-sample config (ma_window=252, eval_frequency_days=21)

| Symbol | Sharpe | MDD |
|---|---|---|
| XLRE | -0.035 (FAIL, threshold 1.0) | 0.393 (FAIL, threshold 0.25) |
| IYR | -0.148 (FAIL, threshold 1.0) | 0.426 (FAIL, threshold 0.25) |

Both symbols fail Sharpe AND max-drawdown decisively at the grid's
best-performing config. No further validators run given the decisive
full-sample failure (walk-forward/param-sensitivity would not change the
conclusion).

## Decision: REJECTED

Full-sample Sharpe is negative on both REIT-sector proxies at the
grid-best config; the source's own monthly-decision MA trend rule, even in
its best regime slice (low-vol, Sharpe 0.637), doesn't clear this repo's
1.0 Sharpe / 0.25 MDD thresholds. Likely cause: XLRE/IYR (since 2015/2000)
cover a much shorter, more concentrated post-GFC/2020-2022-rate-hike
sample than the source's 1926-2025 RlEst series, and REITs' 2022 rate-hike
drawdown (~-30%+) dominates this shorter window in a way the century-long
backtest smooths over. The monthly-decision design (only re-evaluating
every ~21 trading days) also means the strategy can be "stuck" long
through a multi-week REIT selloff without any intra-period exit.
