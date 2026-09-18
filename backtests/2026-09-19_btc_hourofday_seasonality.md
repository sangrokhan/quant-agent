# BTC/ETH Hour-of-Day Intraday Seasonality (2026-09-19)

**Hypothesis:** Bitcoin's 24/7 market shows a robust intraday-hour seasonal
pattern (peak avg returns ~21:00-23:00 UTC per Quantpedia's "The Seasonality
of Bitcoin", summarized in
https://www.quantifiedstrategies.com/bitcoin-intraday-seasonality-trading-strategy/,
read via browser_exec after `web_search` DDGS backend returned no usable
results for the seed queries this iteration). Strategy: hold BTC/ETH only
during a narrow UTC hour window each day, flat otherwise, optionally gated
by a long-horizon SMA trend filter.

**Strategy file:** `strategies/2026-09-19_btc_hourofday_seasonality.py`
(crypto-only — the equity loader here is daily-only, so this genuinely
intraday-seasonality idea cannot be tested honestly on equities with
available data).

## Step 6 grid summary

Grid: `entry_hour` in {20,21,22} x `exit_hour` in {22,23,0} x
`trend_window` in {0, 4800h (~200d)}, BTC/USDT + ETH/USDT, vol_regime_splits=3.

- total_cells: 108, passed_cells: 0, **pass_fraction: 0.0**
- by_asset_class: crypto 0/108
- by_vol_regime: low 0/36, mid 0/36, high 0/36
- best_cell: entry_hour=20, exit_hour=22, trend_window=4800, ETH/USDT, mid-vol tercile, Sharpe 0.495
- worst_cell: entry_hour=22, exit_hour=23, trend_window=0, BTC/USDT, high-vol tercile, Sharpe -0.222

Full raw grid: `grid_result_btc_hourofday.json`.

## Step 7 single-config validation (best grid params: entry_hour=20, exit_hour=22, trend_window=4800)

| Validator | ETH/USDT | BTC/USDT | Threshold |
|---|---|---|---|
| Sharpe (full-sample, gross) | 1.619 (PASS) | 1.624 (PASS) | >= 1.0 |
| Max drawdown | 0.123 (PASS) | 0.090 (PASS) | <= 0.25 |
| Walk-forward (4 splits) | 4/4 positive (PASS) | 4/4 positive (PASS) | >= 0.75 |
| Transaction cost survival (10bps/trade, ~1 round-trip/day) | net Sharpe **-0.120 (FAIL)** | net Sharpe **-0.187 (FAIL)** | >= 0.5 |
| num_trades | 2828 | 2994 | — |

Full raw validators: `validators_btc_hourofday.json`.

## Decision: REJECTED

Gross full-sample Sharpe (1.6+) and walk-forward (4/4 splits) both look
excellent, and the tercile-level grid failure is explained by the same root
cause at finer granularity (per-regime sub-samples have too few
observations for the daily 1-trade round-trip to clear a Sharpe bar). The
decisive failure is **transaction cost survival**: with an entry/exit
window as narrow as 2 hours, the strategy re-enters and re-exits almost
every single day (~2800-3000 round trips over the ~7.5y sample), and even a
modest realistic 10bps/round-trip cost assumption flips net Sharpe strongly
negative for both BTC/USDT and ETH/USDT. The raw seasonal edge (if real) is
too small to survive real-world trading costs at daily turnover frequency.

**Future rescue angle:** only take the position on days when a coarser
signal is also favorable (e.g. trend filter combined with a *multi-day*
hold instead of daily in/out), or use a wider window / lower turnover
version (e.g. weekly rebalance based on average recent hour-of-day
performance) to cut trade count by an order of magnitude before the
transaction-cost check would have a chance of passing.
