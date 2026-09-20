# Abdi-Ranaldo Spike-Fade Strategy — Backtest Report (2026-09-21)

## Hypothesis

Per Abdi & Ranaldo (2017, Review of Financial Studies) "A Simple Estimation
of Bid-Ask Spreads from Daily Close, High, and Low Prices" — read via
metricgate.com's worked methodology page
(https://metricgate.com/docs/abdi-ranaldo-spread-estimator/, plus
conceptual background from
https://quantmemo.com/concepts/abdi-ranaldo-spread-estimator, after
`web_search`'s DDGS backend TLS-erroring on the initial formula query) —
the estimator recovers an effective bid-ask spread from the cross-product
of the close's deviation from the day's log mid-range on consecutive days:
S² = 4·E[(c_t−η_t)(c_t−η_{t+1})], truncated at zero and square-rooted.

Distinct mechanism from this repo's already-accepted Corwin-Schultz
liquidity-regime TREND FILTER (2026-09-20-154): this strategy uses a
transient SPIKE in the rolling Abdi-Ranaldo spread estimate as a DIRECT
contrarian mean-reversion TRIGGER on down days, rather than as a regime
gate for an independent trend signal. First Abdi-Ranaldo-based strategy in
this repo.

## Single-config validators (grid-best config: BTC/USDT, `ar_window=20,
spike_pctile_threshold=0.9, hold_days=3`)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.980 | ≥ 1.0 (very near-miss) |
| Max drawdown | ✅ | 0.225 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 88 trades) | ✅ | net Sharpe 0.916 | ≥ 0.5 |
| Walk-forward (4 splits, manual fallback) | ✅ | 0.75 pass fraction | ≥ 0.75 (exactly at threshold) |
| Parameter sensitivity (12-combo grid, relative std) | ❌ | 0.780 | ≤ 0.5 |

Full sample: 2018-01-01 to 2026-09-01, daily bars.

## Grid test summary (Step 6)

Grid: `ar_window ∈ {15,20} × spike_pctile_threshold ∈ {0.8,0.85,0.9} ×
hold_days ∈ {3,5}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime
terciles = 144 cells.

- **Overall pass fraction: 0.0417 (6/144)** — weak
- By asset class: equity 2/72 (0.028), crypto 4/72 (0.056)
- By vol regime: low 1/48, mid 2/48, high 3/48
- Best cell: BTC/USDT, high-vol tercile, `ar_window=20,
  spike_pctile_threshold=0.9, hold_days=3` — Sharpe 1.516
- Worst cell: QQQ, low-vol tercile, `ar_window=15,
  spike_pctile_threshold=0.9, hold_days=5` — Sharpe -1.279

**Honest scope**: this is a very close near-miss (Sharpe 0.980, just under
the 1.0 bar) with 3 of 5 validators passing, but the parameter-sensitivity
failure (0.780 relative std across the 12-combo BTC/USDT grid) indicates
the edge is not stable across nearby threshold/window choices — a
meaningfully different parameter combo in the same grid produces a much
weaker or negative Sharpe, which is a genuine fragility signal rather than
a borderline-pass artifact.

## Decision

**Reject.** 2 of 5 validators fail (Sharpe near-miss, parameter
sensitivity decisively fails). Strategy file and report kept as a record
of a rejected attempt. A future iteration could revisit with a coarser/
more robust threshold selection (e.g. fixed absolute percentile rather
than a fine grid) if the underlying dislocation-fade intuition is worth
retesting.

Sources visited this iteration:
- https://metricgate.com/docs/abdi-ranaldo-spread-estimator/ (primary source, exact formula and R code example)
- https://quantmemo.com/concepts/abdi-ranaldo-spread-estimator (conceptual background)
