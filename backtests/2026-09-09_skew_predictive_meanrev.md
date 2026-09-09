# 2026-09-09 — Skew-Predictive Mean Reversion (rejected)

**Hypothesis** (id `2026-09-09-112`): Time-series single-asset adaptation of
Dean Markwick's "Cross Asset Skew" replication
(https://dm13450.github.io/2024/02/08/Cross-Asset-Skew-A-Trading-Strategy.html,
itself replicating Baltas's cross-asset skew paper). Source finding
(cross-sectional): negative-skew assets tend to mean-revert upward (a
cluster of sharp down-days has statistically overshot), positive-skew assets
tend to revert downward. Adapted here single-asset: go long when the asset's
own rolling skewness of daily returns drops to/below `entry_skew_threshold`
(sufficiently negative), exit when skew recovers to/above
`exit_skew_threshold`, or a `max_hold_days` time-stop. Distinct from prior
skew entries in this repo (2026-09-05-029 CBOE SKEW index as a vol-regime
gate; 2026-09-08-055/154 skewness as a REGIME FILTER for a separate trend
signal) — this trades skew's own predictive direction directly as the
entry/exit signal, per the source's literal mean-reversion mechanism.

Strategy file: `strategies/2026-09-09_skew_predictive_meanrev.py`

## Step 6 grid summary (skew_window ∈ {40,60,90} × entry_skew_threshold ∈ {-0.5,-0.8} × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles, 72 cells)

- `pass_fraction`: 0.125 (9/72)
- `by_asset_class`: equity 9/36, crypto 0/36 (decisive crypto failure)
- `by_vol_regime`: low 9/24, mid 0/24, high 0/24 — passes exclusively in
  low-vol regime slices
- `best_cell`: skew_window=90, entry_skew_threshold=-0.5, SPY, low-vol
  regime, Sharpe 1.84
- `worst_cell`: skew_window=40, entry_skew_threshold=-0.8, SPY, mid-vol
  regime, Sharpe -0.19

## Single-config validators (best grid config: skew_window=90, entry_skew_threshold=-0.5), full 2019-2026 sample

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.539 ❌ | 0.595 ❌ | ≥ 1.0 |
| Max drawdown | 0.272 ❌ | 0.322 ❌ | ≤ 0.25 |
| TC survival (10bps/trade) | 0.462 ❌ | 0.495 ❌ | ≥ 0.5 net Sharpe |
| Trades | 82 | 90 | — |

(Walk-forward skipped — grid + full-sample validators already decisively
fail every metric; not worth the extra compute per `suggested_workload=max`
scoping guidance of running whichever subset is relevant.)

## Verdict: **reject** (both QQQ and SPY)

Full-sample Sharpe, max drawdown, and TC-survival all fail decisively for
both equities despite an attractive best-grid-cell Sharpe of 1.84
(SPY, low-vol regime only, 1/8 param×asset combos). Crypto fails 0/36 grid
cells entirely. Like the prior CBOE-SKEW-index attempt (2026-09-05-029), a
raw skewness-based signal does not survive full-sample/cross-regime testing
on this repo's daily-bar QQQ/SPY/BTC/ETH setup — the source paper's edge is a
cross-sectional (relative-to-peers) ranking effect across dozens of
futures/ETFs simultaneously, not a single-asset absolute-threshold signal;
this is the second time in this repo a cross-sectional Quantpedia/academic
finding has failed to translate into a single-asset time-series adaptation
(see also 2026-09-09-111 momentum×high-vol, same pattern) — worth treating
cross-sectional-ranking papers as lower-priority candidates for future
single-asset adaptation attempts unless a genuine cross-sectional multi-asset
implementation becomes feasible in this repo.
