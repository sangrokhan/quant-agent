# 2026-09-18-075: Elastic Volume-Weighted Moving Average (eVWMA) Price Crossover

## Hypothesis

Per LuxAlgo's Elastic Volume-weighted MA concept page
(https://www.luxalgo.com/library/concept/elastic-volume-weighted-ma/),
Christian Fries' eVWMA (Technical Analysis of Stocks & Commodities, 2001)
is a recursive average whose smoothing weight per bar is that bar's OWN
SHARE of a trailing volume budget N: `eVWMA_t = ((N_t - V_t) * eVWMA_{t-1}
+ V_t * P_t) / N_t`, seeded `eVWMA_0 = P_0`. High-volume bars pull the
line sharply toward price; low-volume bars barely move it -- a
participation-adaptive average that self-regulates across regimes without
retuning. Hypothesis: price crossing above/below this line signals a
trend change with less lag during high-volume events than a comparable
fixed EMA/SMA, while resisting whipsaws during quiet drift.

Source: https://www.luxalgo.com/library/concept/elastic-volume-weighted-ma/

First eVWMA strategy in this repo (zero prior matches for "EVWMA"/"elastic
volume weighted" in strategies_index.jsonl) -- distinct from fixed-window
VWMA (already tested) and Anchored VWAP (session/pivot-anchored) since
eVWMA's recursive volume-share weighting has no fixed window boundary.

## Step 6 grid summary

`param_grid={vol_lookback: [10,20,40], max_hold_days: [15,30]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2018-01-01..2026-09-01.

- total_cells=72, passed_cells=24, pass_fraction=0.333
- by_asset_class: equity 18/36, crypto 6/36
- by_vol_regime: low 18/24, mid 6/24, high 0/24
- best_cell: SPY low-vol, vol_lookback=20, max_hold_days=15, Sharpe 2.53
- Best average-across-regimes config: QQQ, vol_lookback=40,
  max_hold_days=15, avg Sharpe 1.112, pass 2/3 vol regimes.

## Single-config validation (vol_lookback=40, max_hold_days=15,
2018-01-01..2026-09-01, all 4 symbols tested for full asset-class breadth)

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT | Threshold |
|---|---|---|---|---|---|
| Sharpe ratio | 0.969 (fail) | 0.991 (fail) | 0.991 (fail) | 0.773 (fail) | 1.0 |
| Max drawdown | 0.240 (pass) | 0.201 (pass) | 0.506 (**fail**) | 0.737 (**fail**) | 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.609 (pass), 277 trades | 0.501 (pass), 281 trades | 0.870 (pass), 323 trades | 0.687 (pass), 330 trades | 0.5 |
| Walk-forward (4 splits, manual substitute) | 1.00 (4/4, pass) | 0.75 (3/4, pass) | 1.00 (4/4, pass) | 1.00 (4/4, pass) | 0.75 |
| Parameter sensitivity (relative std, 6-combo grid) | 0.027 (pass) | 0.124 (pass) | 0.073 (pass) | 0.042 (pass) | 0.5 |

## Decision

**Rejected -- consistent near-miss across all four symbols.** Sharpe ratios
of 0.969 (QQQ), 0.991 (SPY), 0.991 (BTC/USDT), and 0.773 (ETH/USDT) are all
tantalizingly close to but below the 1.0 threshold, with remarkably LOW
parameter sensitivity (relative std 0.03-0.12 across all four) -- the most
stable, consistent grid result of any strategy tested this cron trigger,
suggesting the eVWMA crossover mechanic captures a genuine, small,
consistent edge rather than being a fragile overfit. Crypto (BTC/USDT,
ETH/USDT) additionally fails max drawdown decisively (0.506, 0.737 vs
0.25) -- eVWMA's high-volume-driven fast-tracking behavior appears to whip
into large crypto drawdowns during volume-spike liquidation events.

This is one of the closest near-misses seen this cron trigger (SPY and
BTC/USDT both at 0.99). A future revisit could try: (a) adding a
volatility-regime gate (given the grid shows the edge concentrated in
low-vol regimes, 18/24 pass there vs 0/24 in high-vol) to filter out the
high-vol drawdown-inducing periods explicitly, following this repo's
established vol-regime-gate pattern; or (b) a slightly longer max_hold_days
combined with the vol_lookback=40 config specifically for equity (QQQ/SPY
only, dropping crypto given its decisive MDD failure).
