# Ehlers Distance Coefficient Filter (EDCF) price crossover (2026-09-18)

## Hypothesis

John F. Ehlers' Distance Coefficient Filter (EDCF, "Rocket Science For
Traders" 2001, Chapter 18) is a distance-weighted moving average: each bar
in a trailing window is weighted by the sum of its squared distances to
every other bar in that same window -- outlier/turning-point bars pull the
filter toward the window's dominant price cluster more strongly than bars
similar to their neighbors. Distinct weighting logic from every prior
moving-average variant tested in this repo.

Signal: long entry when close crosses above the EDCF line, exit on the
mirror cross below, or a max_hold_days time-stop.

Source: https://www.tradingview.com/script/6a8CD4JI-Ehlers-Distance-Coefficient-Filter/
(open-source Pine Script v3 by everget, MIT license, fully disclosed
formula; fetched via browser_exec -- web_search DDGS backend failing this
cron trigger). First Distance Coefficient Filter strategy in this repo.

## Grid test

`length in {10,14,20} x max_hold_days in {15,20,30}`, equity=[QQQ,SPY]
crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2018-01-01..2026-09-01:

- total_cells=108, passed_cells=35, **pass_fraction=0.324**
- by_asset_class: equity 30/54, crypto 5/54
- by_vol_regime: low 23/36, mid 9/36, high 3/36 -- edge concentrated in
  low-vol regimes but present (weakly) across all three, unlike most
  prior near-miss strategies this cron trigger which showed zero high-vol
  pass cells.
- best_cell: length=20/max_hold_days=30, SPY low-vol, Sharpe 2.84.

## Single-config validation (widened full-sample search:
length=18, max_hold_days=30)

| Symbol | Sharpe | MDD |
|---|---|---|
| QQQ | 0.987 (fail, thr 1.0) | 0.281 (fail, thr 0.25) |
| SPY | 1.069 (**pass**) | 0.207 (**pass**) |

A wider grid search (length in {10..40}, max_hold_days in {15..60})
found the above as the best min-across-symbols full-sample config: SPY
clears both thresholds, but QQQ misses Sharpe by 0.013 and MDD by 0.031 --
an extremely tight near-miss.

Original best-avg config (length=20, max_hold_days=30) validator run
(4-symbol):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe, 10bps) | Trades |
|---|---|---|---|---|
| QQQ | 0.990 (fail) | 0.291 (fail) | 0.834 pass | 124 |
| SPY | 0.844 (fail) | 0.213 pass | 0.632 pass | 131 |
| BTC/USDT | 0.104 (fail) | 0.749 (fail) | -0.044 (fail) | 5534 |
| ETH/USDT | 0.211 (fail) | 0.715 (fail) | -0.004 (fail) | 5321 |

Crypto's very high trade count reflects `load_crypto`'s hourly-bar default
granularity mismatched with a filter tuned for daily bars (same caveat as
other recent entries this cron trigger).

## Verdict: REJECTED (equity near-miss; crypto decisive fail)

Both grid-search passes land right at the edge of the threshold for one
symbol while missing on the other (QQQ Sharpe 0.987-0.990, both configs;
SPY ranges from 0.844 to 1.069 depending on config). This is one of the
tightest near-misses this cron trigger -- a future revisit could try
per-symbol parameter retuning (QQQ vs SPY separately, this repo's
established rescue pattern) or an MDD-focused overlay specifically for
QQQ, since SPY already clears both thresholds at length=18/hold=30.
