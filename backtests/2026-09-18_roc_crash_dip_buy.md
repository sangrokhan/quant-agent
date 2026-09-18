# ROC "Crash" Dip-Buy — Backtest Report

**Date:** 2026-09-18
**Strategy file:** `strategies/2026-09-18_roc_crash_dip_buy.py`
**KB id:** 2026-09-18-131

## Hypothesis

Source: [QuantifiedStrategies.com — Bitcoin Crash Trading Strategy: Backtest Analysis](https://www.quantifiedstrategies.com/bitcoin-crash-trading-strategy/)
(visited this iteration via `browser_exec` — `web_search`'s DuckDuckGo/DDGS backend
returned unrelated/garbage results for TASC-archive queries this iteration, so
Google SERP fallback was used from the start).

Source's own disclosed mechanical rule: compute ROC(N) over the last N days;
if ROC(N) <= -roc_drop_pct, buy at the close; exit at the close after N days
(same N for lookback and hold). Source's own optimization grid: ROC drop in
{5,10,...,25}%, N in {10,...,100} days, tested on Bitcoin only, with the
source's own stated conclusion: "the results are pretty erratic... you don't
have to be a genius to understand that this is not a tradable strategy."

This iteration re-implemented the same rule generically and tested it across
both equity (QQQ) and crypto (BTC/USDT) per this repo's standard grid
protocol, rather than trusting the source's single-asset, candidly-skeptical
conclusion at face value.

## Grid summary (Step 6)

`param_grid={"roc_window": [10, 20], "roc_drop_pct": [10.0, 20.0]}`,
`symbols={"equity": ["QQQ"], "crypto": ["BTC/USDT"]}`, `vol_regime_splits=3`.

- total_cells: 24, passed_cells: 0, **pass_fraction: 0.0**
- by_asset_class: equity 0/12, crypto 0/12
- by_vol_regime: low 0/8, mid 0/8, high 0/8
- best_cell: roc_window=10, roc_drop_pct=10.0, crypto BTC/USDT, high-vol regime, Sharpe **1.199** (still below the grid pass threshold's other requirements / not a persistent edge)
- worst_cell: roc_window=10, roc_drop_pct=10.0, equity QQQ, mid-vol regime, Sharpe **-0.758**

## Decision

**Rejected** at the grid stage (0/24 cells pass) — decisive, no single-config
validator run warranted given the grid found no viable cell in either asset
class or any vol regime. This directly corroborates the source's own stated
finding that the raw ROC-crash-dip-buy rule is not a tradable strategy as
disclosed; unlike several other TASC/QS "rescued as continuous sizing dial"
patterns in this repo, this one is a single fixed-hold event trigger with no
natural continuous transform, and the underlying premise (any post-decline
bounce is directly tradable with a naive time-stop) does not show even a
diluted edge across regimes.

Light-workload note: given the gate blocked (5h rolling usage at 100%)
partway through this iteration, only Step 6 (grid) was run; Step 7's full
single-config validator suite (Sharpe/MDD/TC/walk-forward/param-sensitivity)
was skipped since the grid result was already decisively negative across all
24 cells — consistent with RESEARCH_LOOP.md Step 7's guidance to scope
validator depth to `suggested_workload`.
