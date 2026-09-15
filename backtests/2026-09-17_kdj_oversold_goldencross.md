# 2026-09-17: KDJ Oversold Golden-Cross Mean-Reversion — REJECTED

## Hypothesis

Per https://blog.itick.io/en/technical-analysis/kdj-trading-strategies
("Overbought/Oversold Strategy"): buy when K, D, and J are all below 20
(oversold zone) AND K crosses above D (golden cross); exit when K, D, J
are all above 80 (overbought zone) AND K crosses below D (death cross).
KDJ is a stochastic-oscillator derivative (%K/%D standard stochastic,
%J = 3*%K - 2*%D, an amplified early-warning line). First KDJ strategy
tested in this repo (zero prior KDJ entries in strategies_index.jsonl).

Source: https://blog.itick.io/en/technical-analysis/kdj-trading-strategies
(read via browser_exec fallback this iteration — web_extract's DDGS
backend cannot extract URL content, "search-only backend" error).

## Strategy file

`strategies/2026-09-17_kdj_oversold_goldencross.py`

## Step 6 — Grid test

Grid: `k_window` in [9,14,21], `oversold_thresh` in [15,20,25],
`overbought_thresh` in [75,80]; symbols equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT];
vol_regime_splits=3. 216 total cells.

- pass_fraction: **17/216 = 0.079**
- by_asset_class: equity 10/108, crypto 7/108
- by_vol_regime: low 7/72, mid 8/72, high 2/72
- best_cell: k_window=21, oversold_thresh=15, overbought_thresh=75, QQQ, mid-vol, Sharpe=1.557
- worst_cell: k_window=9, oversold_thresh=15, overbought_thresh=75, BTC/USDT, low-vol, Sharpe=-1.018

Edge is thin and regime-concentrated (mid-vol slightly ahead of low/high,
but no regime clears even 15% pass rate).

## Step 7 — Standard validators (primary config: best_cell params)

`k_window=21, oversold_thresh=15, overbought_thresh=75, k_smooth=3, d_smooth=3, max_hold_days=15`

| Symbol | Sharpe | MDD | TC net Sharpe | WF pass_fraction |
|---|---|---|---|---|
| QQQ | 0.527 (fail, thr 1.0) | 0.255 (fail, thr 0.25) | 0.477 (fail, thr 0.5) | 0.75 (pass) |
| SPY | 0.014 (fail) | 0.269 (fail) | -0.033 (fail) | 0.25 (fail) |

Walk-forward used a manual 4-fold range split (vectorbt's
`utils.splitting.RangeSplitter` unavailable in this environment's
installed vectorbt version, as noted in several prior iterations).

## Decision (Step 8)

**Rejected.** Full-sample Sharpe/MDD/transaction-cost-survival all fail on
both equity symbols despite the grid's best single cell reaching a
promising Sharpe of 1.56 — that cell is a narrow mid-vol-regime/single-symbol
artifact, not a generalizable edge. Grid pass_fraction (0.079) is far below
prior accepted strategies' typical range (~0.2-0.3+).

## Notes for future loops

- KDJ's overbought/oversold+cross condition is essentially a
  stricter/leveraged variant of plain stochastic crossover + Stochastic
  RSI — both already tested and mostly rejected in this repo (see
  `strategies_index.jsonl` stochastic/Stochastic-RSI entries) — so this
  result is consistent with that prior pattern rather than surprising.
- Not revisited: J-line breakout (>100/<0 extreme readings) and
  divergence variants from the same source, which use different entry
  logic and could be tried in a future iteration if KDJ family is
  revisited.
