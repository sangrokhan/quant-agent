# January Effect small-cap (IWM) seasonal window — REJECTED

**Hypothesis source:** "January Effect" (Rozeff & Kinney 1976), Yale
Hirsch's Stock Trader's Almanac, QuantifiedStrategies.com "200 Trading
Strategies" roundup, corroborated by StatsEdgeTrading video summary (all
found via `browser_exec` Google SERP fallback -- `web_search` returned no
results/TLS errors on multiple queries this iteration). Small-cap stocks
(proxied by IWM) historically outperform large caps in a window from
mid-December through mid-January, attributed to December tax-loss-selling
pressure reversing in the new year plus institutional window-dressing.

This repo has never traded IWM before, nor tested this specific
December-to-January small-cap seasonal window (distinct from the existing
4-Year Presidential Election Cycle and general Santa Claus Rally entries).

## Grid test (Step 6)

`entry_day ∈ {1, 10, 15, 20} × exit_day ∈ {10, 15, 25}`, symbols =
IWM/SPY (equity) + BTC/USDT/ETH/USDT (crypto falsification check),
vol_regime_splits=3, 144 total cells.

- **pass_fraction: 0.111** (16/144 cells passed)
- **by_asset_class:** equity 12/72, crypto 4/72
- **by_vol_regime:** low 13/48, mid 0/48, high 3/48 — edge concentrated in
  low-vol tercile only
- **best_cell:** entry_day=1, exit_day=15, **SPY** (not IWM!) low-vol
  tercile, Sharpe 1.84 — notably, the best cell is on SPY (large-cap), not
  IWM (small-cap), which already undermines the "small-cap-specific" thesis
  of the January Effect as tested here.

## Single-config validation (Step 7) — entry_day=1, exit_day=15

| Symbol | Sharpe (full period) | MDD | TC-survival net Sharpe |
|---|---|---|---|
| SPY | 0.012 (FAIL, thresh 1.0) | 0.193 (PASS, thresh 0.25) | -0.033 (FAIL, thresh 0.5) |
| IWM | 0.022 (FAIL, thresh 1.0) | 0.286 (FAIL, thresh 0.25) | -0.012 (FAIL, thresh 0.5) |

## Verdict: REJECTED

Full-period performance is decisively flat-to-negative on both SPY and
IWM — the grid's best-cell Sharpe of 1.84 is a single-tercile cherry-pick,
not representative. Critically, IWM (the source's own primary small-cap
proxy) performs WORSE than SPY (large-cap control) on every metric tested,
directly contradicting the small-cap-specific premise of the January
Effect hypothesis as implemented here — with only 22 trades/round-trips
over an 11-year sample, the strategy also has far too few independent
observations for statistical confidence even before the outright Sharpe/TC
failures. Consistent with widely-documented findings that the January
Effect has weakened/disappeared in recent decades as it became widely known
and arbitraged away.
