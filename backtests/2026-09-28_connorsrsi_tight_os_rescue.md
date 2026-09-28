# ConnorsRSI Tight-Oversold Rescue Attempt — Backtest Report (failed rescue)

**Date:** 2026-09-28
**Follow-up to:** 2026-09-28-044 (ConnorsRSI composite, near-miss — SPY/QQQ/ETH Sharpe 0.89-0.95, TC-survival failed at oversold_threshold=15/100-105 trades)

## Hypothesis

2026-09-28-044's own notes recommended a tighter `oversold_threshold`
(5-10, per Connors' own more-conservative recommendation) to cut trade
frequency and transaction-cost drag while preserving per-trade edge. This
iteration tests that specific rescue direction with oversold_threshold ∈
{3, 5, 8} on equity (QQQ/SPY) + ETH/USDT (BTC/USDT excluded per the prior
iteration's explicit recommendation not to revisit without a different
mechanism).

## Grid test summary (oversold_threshold∈{3,5,8} × exit_threshold∈{40,50} × max_hold_days∈{8,10}, QQQ/SPY/ETH-USDT × low/mid/high vol terciles)

- total_cells: 108, passed_cells: 10, **pass_fraction: 0.093** (worse than the original 15-threshold grid's 0.194)
- by_asset_class: equity 10/72; crypto (ETH) 0/36 — tightening made ETH *worse*, not better
- Best full-sample-weighted config: SPY oversold_threshold=8/exit_threshold=40/max_hold_days=8, avg grid Sharpe 0.827 (worse than the original threshold=15 config's 1.162)

## Single-config validation (SPY, oversold_threshold=8, exit_threshold=40, max_hold_days=8)

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Sharpe | 0.275 | 1.0 | **FAIL** (collapsed from 0.952 at threshold=15) |
| MDD | 0.081 | 0.25 | PASS |
| TC-survival (net Sharpe) | 0.144 | 0.5 | **FAIL** (worse than 0.404 at threshold=15, despite only 22 trades vs 105 — the fewer trades that DO fire are lower-quality) |

## Decision: **REJECT** (rescue attempt failed)

The hypothesized fix (tighter oversold_threshold reduces trade count and
improves per-trade quality) does NOT hold empirically — full-sample
Sharpe collapsed from 0.952 to 0.275 despite trade count dropping from 105
to 22. This suggests the original threshold=15's higher trade frequency
was actually diluting a *better* edge concentrated at the less-extreme
oversold readings, not diluting a worse one — i.e. the strategy's edge
comes from moderate/frequent oversold dips, not from waiting for rarer
extreme readings. This closes off the tighter-threshold rescue path
recommended by 2026-09-28-044; the ConnorsRSI composite family should not
be revisited via this specific lever again without a fundamentally
different fix (e.g. reducing trade cost assumption sensitivity, or
retesting exit_threshold/max_hold_days independently of oversold_threshold).
