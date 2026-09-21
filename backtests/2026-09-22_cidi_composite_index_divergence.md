# Backtest Report: CIDI (Composite Index Divergence Indicator) Oversold Bounce

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_cidi_composite_index_divergence.py`
**Source:** https://www.quantifiedstrategies.com/composite-index-divergence-indicator/
(Connie Brown's Composite Index, MTA Journal 1994 "A New Approach for an Old
Problem")

## Hypothesis

CIDI = triple-smoothed unbounded RSI derivative: 9-period momentum of a
14-period RSI, plus a 3-period SMA of a separate 3-period RSI. Source's own
disclosed backtest rule (QQQ, 228 trades, 76% win rate, avg 1%/trade, 17%
MDD, 0.03% costs): long at close when CIDI breaks below 10; exit when close
> prior day's high, or after 7 trading days.

## Step 6 — Grid test summary

Grid: `cidi_entry_threshold` in {5, 10, 15}, `max_hold_days` in {5, 7, 10},
symbols {QQQ, SPY, BTC/USDT, ETH/USDT}, vol_regime_splits=3 (108 cells total).

- **pass_fraction: 0.204** (22/108 cells)
- **by_asset_class:** equity 22/54 pass; crypto 0/54 (decisive fail)
- **by_vol_regime:** low-vol 13/36 pass; mid-vol 0/36 (decisive fail); high-vol 9/36 pass
- **best_cell:** SPY, low-vol regime, `cidi_entry_threshold=5.0, max_hold_days=5`, Sharpe 1.60
- **worst_cell:** ETH/USDT, low-vol regime, `cidi_entry_threshold=10.0, max_hold_days=5`, Sharpe -0.75

The edge is concentrated in low/high vol-regime tercile slices on equities
only; the mid-vol regime uniformly fails, and crypto fails uniformly across
all regimes.

## Step 7 — Single-config validators (grid-best config: threshold=5, hold=5)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** 0.574 | **FAIL** 0.646 |
| Max Drawdown (<=0.25) | PASS 0.123 | PASS 0.171 |
| TC-survival (net Sharpe>=0.5, 10bps/trade) | **FAIL** 0.487 | PASS 0.532 |
| Walk-forward | SKIPPED (library bug: `vectorbt.utils` has no attribute `splitting` in installed vectorbt version — pre-existing tooling issue, not a strategy defect) |
| Parameter sensitivity (relative std <=0.5 across threshold={3,5,8}) | PASS 0.073 | PASS 0.104 |

Full-sample Sharpe on both symbols falls well short of the 1.0 threshold
despite the grid's per-regime-slice best cells clearing 1.5+ — confirming
the grid's own finding that the edge is regime-concentrated, not a genuine
full-sample edge. This is the same failure mode recorded repeatedly in this
knowledge base for near-miss regime-dependent oscillator strategies.

## Step 8 — Decision: REJECT

Rejected on full-sample Sharpe (both QQQ and SPY) and QQQ TC-survival.
MDD and parameter-sensitivity pass cleanly, and the strategy's edge is real
but confined to low/high-vol tercile slices on equities only — a future
iteration could revisit this with an explicit vol-regime gate (only trade
when NOT in the mid-vol tercile) as a direct fix, following this repo's
established regime-gate rescue pattern.

Crypto (BTC/USDT, ETH/USDT) rejected decisively across the entire grid —
CIDI oversold-bounce logic does not transfer to crypto's return distribution.
