# Backtest Report: BB Mean-Reversion with Dual Regime Gate (ATR-percentile + Trend-slope-flatness)

**Strategy file:** `strategies/2026-09-03_bb_meanrev_regime_dualgate.py`
**Date:** 2026-09-03
**Knowledge base id:** 2026-09-03-023

## Hypothesis

Source: [vantixs.com mean-reversion crypto template](https://vantixs.com/blog/mean-reversion-template-crypto-bot)
(fetched via browser_exec after `web_extract` failed — DDGS is a
search-only backend and cannot extract URL content).

Claim: a Bollinger-Band mean-reversion entry (long when close < lower BB)
only has edge when gated by BOTH:
1. **Volatility gate**: ATR(14) is at/below the 75th percentile of its own
   trailing 90-period window (volatility not expanding).
2. **Trend-slope gate**: the 50-period SMA's bar-over-bar percent change is
   within ±0.1% (market is range-bound, not trending).

Source's own reported backtest: adding this dual gate cut max drawdown from
32% to 11% while only giving up ~15% of returns, vs an ungated version
(numbers not independently verifiable — vendor blog, no raw data/code
published).

This is distinct from the earlier-rejected `2026-09-03-001` (QQQ BB
mean-reversion gated only by realized-vol-vs-trailing-median, single gate,
QQQ only, Sharpe -0.30) — this strategy uses a genuinely different two-part
gate construction (ATR-percentile-rank + MA-slope-flatness) and is tested
across both equity and crypto.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`, param grid
`atr_percentile_threshold ∈ {0.6, 0.75, 0.9}` × `slope_threshold ∈
{0.0005, 0.001, 0.002}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3
vol terciles (low/mid/high), 108 cells, 2019-01-01 to 2026-09-01:

- **pass_fraction: 0.139** (15/108 cells)
- **by_asset_class**: equity 15/54, crypto 0/54
- **by_vol_regime**: low 9/36, mid 4/36, high 2/36
- **best_cell**: QQQ, `atr_percentile_threshold=0.9, slope_threshold=0.002`,
  low-vol tercile, Sharpe 1.79 (narrow-slice)
- **worst_cell**: QQQ, `atr_percentile_threshold=0.75, slope_threshold=0.002`,
  mid-vol tercile, Sharpe -1.46

## Single-config validation (Step 7)

| Config | Symbol | Sharpe | Threshold | MDD | Net Sharpe (10bps/trade) | Trades |
|---|---|---|---|---|---|---|
| Primary (source default: atr_pct=0.75, slope=0.001) | QQQ | **-0.248** (fail) | 1.0 | 5.6% (pass) | -0.355 (fail) | 22 |
| Grid-best (atr_pct=0.9, slope=0.002) | QQQ | **0.045** (fail) | 1.0 | 19.4% (pass) | -0.064 (fail) | 44 |
| Grid-best (atr_pct=0.9, slope=0.002) | SPY | **0.857** (fail, close) | 1.0 | 7.6% (pass) | 0.640 (**pass**) | 56 |

Parameter sensitivity (QQQ, full 3×3 grid, full-sample Sharpe):
relative_std = **20.53** vs threshold 0.5 (fail — Sharpe values range from
strongly negative to positive across the grid with a mean near zero,
i.e. essentially noise, not a robust edge).

## Decision: REJECTED

Every full-sample Sharpe at every tested config (source's own recommended
default, and the grid-best config) fails the ≥1.0 threshold outright on
QQQ; SPY grid-best comes closest (0.857) but still fails. Parameter
sensitivity fails catastrophically (rel.std 20.5, an order of magnitude
over the 0.5 ceiling) — the strategy's Sharpe is essentially random noise
across nearby gate-threshold choices, not a stable edge. Crypto rejected
decisively (0/54 grid cells) — the dual gate construction (ATR-percentile +
MA-slope-flatness), tuned in the source article's own BTC/USDT
4H-timeframe context, does not translate to this repo's daily-bar BTC/ETH
data.

Max drawdown and (in one cell) transaction-cost survival did pass, echoing
the source's own claim that the gate is effective at *risk containment*
(MDD stayed low, 5.6%-19.4%, well under the 25% ceiling in every tested
config) — but risk containment alone does not produce a positive,
stable edge; a strategy that rarely trades and rarely loses much can still
have a negative or noise-level Sharpe, which is what happened here.

## Notes for future loops

- The dual-gate MECHANISM (vol-percentile + trend-slope) is a genuinely new
  regime-filter construction for this repo (distinct from realized-vol-vs-
  median in -001 and the accepted `low_vol_percentile` gate in -021's
  SMA-crossover strategy). It doesn't help a Bollinger mean-reversion entry
  here, but the same gate could be tried on a different entry signal in a
  future iteration.
- The 15/54 equity passing cells are concentrated in narrow low-vol-tercile
  slices, not full-sample performance — a recurring pattern in this log
  where grid `best_cell` results are optimistic vs. the full-sample
  single-config check (see -018, -020, -022 for the same phenomenon).
- `walk_forward` skipped this iteration (workload=max but full-sample Sharpe
  already failed decisively at both tested configs — a stricter
  out-of-sample check cannot flip that outcome, consistent with the
  precedent set by -001).
