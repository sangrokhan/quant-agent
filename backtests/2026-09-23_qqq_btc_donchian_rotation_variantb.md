# QQQ/SPY-BTC Donchian Breakout Rotation (Variant B: Crypto-First) — Backtest Report

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_qqq_btc_donchian_rotation_variantb.py`
**Outcome:** ACCEPTED (QQQ and SPY, all 5 validators pass at `lookback=10`)

## Hypothesis + source

Direct follow-up to accepted 2026-09-23-057 (Variant A, equity-first
priority). Same source (Vojtko & Dujava, "Silicon vs. Satoshi: Tactical
Asset Rotation Between NASDAQ-100 and Bitcoin", SSRN 7055018,
https://quantpedia.com/silicon-vs-satoshi-tactical-asset-rotation-between-nasdaq-100-and-bitcoin/),
this iteration tests the paper's own explicitly-disclosed **Variant B**:
BTC checked FIRST for a breakout (hold BTC if breaking out), else check
equity (hold equity if breaking out), else cash. The paper's own reported
finding: Variant B produces higher absolute returns at short lookbacks
(5-day CAGR 47.06%, highest across all configs) with elevated volatility
(33.11%), and degrades faster at long lookbacks (50-day Sharpe 0.846,
below all benchmarks). This iteration mechanically swaps only the priority
ordering (same breakout signal, same cash fallback) against this repo's own
data/loaders.py-sourced QQQ/SPY/BTC series.

## Grid summary (Step 6)

`run_strategy_grid`: `param_grid={lookback:[10,20,30]}`,
`symbols={equity:[QQQ,SPY]}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01. 18 cells total.

- **pass_fraction: 0.722** (13/18) — identical overall fraction to Variant A
- **by_vol_regime:** low 2/6; mid 5/6; **high 6/6** — again strongest in
  high-vol regimes (cash-fallback benefit), but WEAKER than Variant A in
  the low-vol tercile (2/6 vs Variant A's 5/6)
- **best_cell:** QQQ, lookback=10, low-vol tercile, Sharpe 1.83
- **worst_cell:** SPY, lookback=30, low-vol tercile, Sharpe 0.50

## Single-config validators (QQQ, SPY; `lookback=10` — paper's own finding that
Variant B favors short lookbacks; 10 is the shortest value in this
iteration's grid, 2019-01-01 to 2026-09-01)

| Validator | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 1.506 | 1.447 | >= 1.0 | **PASS** (both) |
| Max drawdown | 0.218 | 0.190 | <= 0.25 | PASS (both) |
| TC survival (10bps/trade, 268/284 trades) | 1.288 | 1.213 | >= 0.5 | **PASS** (both) |
| Walk-forward (4 manual date splits — `vbt.utils.splitting.RangeSplitter` still broken, same repo-wide workaround) | 4/4 splits positive (1.0) | 4/4 splits positive (1.0) | >= 0.75 | PASS (both) |
| Parameter sensitivity (lookback 10/20/30 grid-mean Sharpe relative std) | 0.080 | 0.103 | <= 0.5 | PASS (both) |

## Decision (Step 8): ACCEPT (QQQ, SPY)

All 5 validators pass on both symbols. SPY's Sharpe (1.447) is notably
higher than Variant A's SPY Sharpe (1.221), matching the paper's own
observation that BTC-first ordering can outperform at short lookbacks —
though QQQ's max drawdown (0.218) sits closer to the 0.25 threshold than
Variant A's (0.174), consistent with the paper's own note about elevated
volatility under the crypto-first ordering. Both variants are now accepted
and coexist in `strategies/` — a future loop could consider whether an
ensemble/blend of the two orderings improves on either alone (noted here,
not pursued this iteration per RESEARCH_LOOP.md's one-hypothesis-per-
iteration rule).
