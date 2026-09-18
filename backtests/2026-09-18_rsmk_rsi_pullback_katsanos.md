# 2026-09-18 — RSMK relative-strength pullback-in-uptrend (Katsanos TASC Oct 2026)

## Hypothesis

Per https://traders.com/Documentation/FEEDbk_docs/2026/10/TradersTips.html
(Python Traders' Tips code by Rajeev Jain implementing Markos Katsanos'
"A Low-Risk ETF Trading Strategy", read via `browser_exec` after `web_search`
DDGS backend returned `"No results found"` for the seed query this
iteration): buy an ETF/asset when it is showing strong relative strength vs
a benchmark (RSMK, Katsanos' own indicator, TASC March 2020) that has just
cooled off (RSI pulling back into oversold and starting to recover) with a
short-term absolute-trend confirmation. This repo simplifies the source's
48-ETF cross-sectional scanner (which requires cross-sectional ranking data
this repo's single-symbol loaders don't support) into a single-symbol
version: candidate asset vs SPY (equity) or vs BTC/USDT (crypto, no natural
"market ETF" analog available via ccxt).

Distinct from this repo's 2 prior RSMK entries (2026-09-09-066 VPN,
2026-09-12-153 plain RSMK/signal-line crossover) via the added RSI(10)
pullback-and-recovery gate — buying strength *during* a pullback rather than
on a raw RSMK crossover.

## Grid summary

`grid_cells_rsmk_rsi_pullback.json` — 324 cells: `rs_bars` in {25,35,50} x
`rsi_oversold` in {30,35,40} x `max_hold_days` in {15,20,30}, QQQ/SPY (equity)
and BTC/USDT/ETH/USDT (crypto), `vol_regime_splits=3`.

- Overall pass_fraction: 56/324 = 17.3%
- by_asset_class: equity 21/162 (13.0%), crypto 35/162 (21.6%)
- by_vol_regime: low 39/108 (36.1%), mid 16/108 (14.8%), high 1/108 (0.9%)
- Best per-symbol mean-Sharpe configs selected for full-sample validation:
  ETH/USDT (rs_bars=25, rsi_oversold=40, max_hold_days=30, mean tercile
  Sharpe 1.33) and QQQ (rs_bars=35, rsi_oversold=30, max_hold_days=30, mean
  tercile Sharpe 1.16).

## Full-sample validators (2019-01-01 to 2026-09-01)

`validators_rsmk_rsi_pullback.json`. Walk-forward used this repo's
established manual 4-way contiguous-split substitute (`validators.py`'s
`check_walk_forward` still errors on the installed vectorbt: `module
'vectorbt.utils' has no attribute 'splitting'`).

| Symbol | Sharpe | MDD | TC-net-Sharpe | Walk-forward | Param-sensitivity |
|---|---|---|---|---|---|
| ETH/USDT | -0.737 (fail, thr 1.0) | 0.999 (fail, thr 0.25) | -0.719 (fail, thr 0.5) | 0/4 splits (fail, thr 0.75) | 0.632 (fail, thr 0.5) |
| QQQ | 0.960 (fail, thr 1.0, near-miss) | 0.025 (pass) | 0.952 (pass) | 1/4 splits (fail, thr 0.75) | 0.590 (fail, thr 0.5) |

ETH/USDT: full-sample result is a decisive collapse (0/5) despite a
promising grid mean-Sharpe of 1.33 — the tercile-grid cells apparently
captured favorable sub-windows that don't hold over the full multi-year
sample (a known grid-vs-full-sample overselection pattern already seen in
this repo, e.g. 2026-09-18-132's Better Volume rescue). MDD of 0.999 signals
the strategy essentially wipes out the account at some point in the
full sample — worth flagging as a likely instability in the exit logic
(RSMK-crosses-below-MA exit can leave a position open across a very long
adverse stretch if RSMK stays marginally above its MA for an extended
period) rather than treating the grid's per-tercile 1.33 Sharpe as
representative.

QQQ: only 1 trade fires over the entire 2019-2026 sample with this config
(vs. the grid's per-tercile sub-slices finding more), so the near-miss
Sharpe of 0.96 and clean MDD/TC-survival numbers rest on a single trade —
not statistically meaningful, and walk-forward correctly flags this (only
1/4 splits positive).

## Decision: REJECT

Both configs fail walk-forward and parameter-sensitivity; ETH/USDT fails
every validator decisively. Full-sample results diverge sharply from the
grid's per-tercile pass results — a fragile, likely-overselected
construction on the RSI-pullback-gated RSMK combination as specified. A
future iteration could revisit with either (a) a shorter/more frequent
lookback so the trend-loss exit tracks conditions closer (avoiding the
extreme MDD), or (b) a hard time-stop shorter than max_hold_days=30 as a
safety net independent of the RSMK-cross exit, or (c) require the exit
condition ALSO checked on an OR basis with a simple stop-loss.

Source: https://traders.com/Documentation/FEEDbk_docs/2026/10/TradersTips.html
(browser_exec fallback; web_search DDGS backend `"No results found"`).
