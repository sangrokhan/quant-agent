# Backtest Report: Kaufman's "Stress" Pairs-Logic Mean Reversion vs SPY

**Strategy file:** `strategies/2026-09-17_kaufman_stress_pairs_meanrev.py`
**Source:** https://traders.com/documentation/feedbk_docs/2014/03/traderstips.html
(TASC March 2014 Traders' Tips, "Timing The Market With Pairs Logic" by
Perry J. Kaufman; TradeStation/CQG/MetaStock/thinkorswim code disclosed
directly; read this iteration via `browser_exec`).

## Hypothesis

Kaufman's Stress indicator double-transforms: a rolling stochastic of the
target close vs its own N-bar high/low range, minus the same stochastic
computed on a reference index (SPY), then a rolling stochastic OF THAT
DIFFERENCE (bounded 0-100). Low Stress (<=10) signals persistent relative
underperformance vs the index -- a pairs-style dip-buy, gated by the
source's own "isReady" reset (Stress must first exceed 50 since the last
crisis-stop exit before a new sub-10 entry arms). Exit at Stress>=50 or a
10% crisis stop. Distinct from repo's existing single-asset
stochastic/relative-strength entries (double stochastic-of-difference
transform, not a plain oscillator).

## Grid test summary (Step 6)

`param_grid={"period": [30,50], "entry_level": [10,20]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01..2026-09-01. (Note: SPY itself is
the fixed reference index in this construction, so testing SPY against
SPY produces a degenerate constant-zero difference series -- see below.)

- **total_cells:** 48, **passed_cells:** 4, **pass_fraction:** 0.083
- **by_asset_class:** equity 4/24 (0.167), crypto 0/24 (0.0) -- decisive crypto failure
- **by_vol_regime:** low 1/16, mid 3/16, high 0/16
- **best_cell:** period=30, entry_level=10, BTC/USDT, high-vol regime, Sharpe=1.49 (isolated outlier)
- **worst_cell:** period=50, entry_level=20, QQQ, high-vol regime, Sharpe=-0.89

Already a very weak grid (0.083 overall pass fraction) before even reaching
single-config validation.

## Single-config validators (Step 7) — grid-best config: period=30, entry_level=10

| Validator | QQQ | SPY (degenerate self-comparison) |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** 0.408 | trivially PASS (Infinity, 0 trades -- SPY-vs-SPY diff is always 0, entry never fires) |
| Max Drawdown (<=0.25) | **FAIL** 0.279 | trivially PASS (0.0, 0 trades) |
| Transaction cost survival (10bps/trade, net Sharpe>=0.5) | **FAIL** 0.257 (110 trades) | trivially PASS (0 trades, no cost) |

SPY's "pass" is a construction artifact (SPY *is* the reference index, so
the diff series is identically zero and no signal ever fires) -- not a real
result. The only meaningful single-config test (QQQ vs SPY) fails all 3
core validators decisively.

## Decision: REJECT

QQQ fails Sharpe, max drawdown, and transaction-cost survival simultaneously
at the grid-optimal config, and the grid overall shows only 0.083 pass
fraction with a decisive 0/24 crypto failure. The double-stochastic-of-
relative-difference construction does not produce a tradeable edge on this
instrument/index pairing over 2019-2026. Not pursued further; strategy file
kept as a record of a rejected attempt.
