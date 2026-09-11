# Backtest Report: Defense-First TAA Gate (QQQ)

**Strategy file:** `strategies/2026-09-11_defense_first_taa_gate.py`
**Hypothesis ID:** 2026-09-11-081

## Hypothesis

Per Thomas Carlson's "Defense First" tactical asset allocation model, as
summarized by QuantifiedStrategies.com
(https://www.quantifiedstrategies.com/alternative-60-40-portfolio/, visited
this iteration): four defensive assets (TLT, GLD, DBC, UUP) are ranked by an
averaged 1/3/6/12-month momentum measure; whenever a defensive asset's
momentum falls below the T-bill (BIL) hurdle rate, that asset's notional
allocation is redirected to US equities (SPY/QQQ) instead. The source's own
key finding is that the *collective* signal (how many of the 4 defensive
assets are simultaneously underperforming) carries more predictive power
than any single defensive asset's signal alone.

Adapted to this repo's single-asset `generate_signals`/`generate_returns`
interface as a **graded continuous weight**: weight = (count of the 4
defensive assets underperforming the BIL hurdle) / 4, rebalanced weekly and
applied to the primary equity/crypto asset. This directly tests the
source's "collective signal strength" claim rather than a binary on/off
circuit breaker (distinct from the previously REJECTED single-asset
gold-momentum gate, id 2026-09-08-147).

## Single-config validator results (QQQ, rf_threshold_bps_per_day=5.0, rebalance_freq="W")

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.261 | ≥ 1.0 |
| Max drawdown | ✅ | 0.128 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 126 trades) | ✅ | net Sharpe 0.978 | ≥ 0.5 |
| Walk-forward (manual 4-split fallback; `vbt.utils.splitting` still broken in this install) | ✅ | 4/4 splits positive | ≥ 0.75 pass fraction |
| Parameter sensitivity (6-combo grid: rf_threshold∈{0,5,15}bps × freq∈{W,ME}) | ✅ | relative_std 0.016 (mean Sharpe 1.227, std 0.019) | ≤ 0.5 |

All 5 validators pass -> **ACCEPTED for QQQ**.

## Step 6 grid summary (param_grid rf_threshold_bps_per_day=[0,5,15] x rebalance_freq=[W,ME], symbols equity=[SPY,QQQ] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2019-01-01 to 2026-09-01)

- total_cells=72, passed=23, **pass_fraction=0.319**
- by_asset_class: equity 23/36 pass, crypto **0/36 decisive reject**
- by_vol_regime: low 12/24, mid 9/24, high 2/24 (edge concentrates in low/mid-vol regimes, weak in high-vol)
- best_cell: SPY, rf=0.0bps, freq=W, low-vol, Sharpe 2.44
- worst_cell: ETH/USDT, rf=15bps, freq=ME, mid-vol, Sharpe 0.04
- QQQ average Sharpe across vol regimes and all param combos: ~1.44-1.55 (best among equity symbols)
- SPY also broadly passes (avg Sharpe ~1.37-1.41) but slightly weaker than QQQ

**Honest scope:** this strategy is accepted for **equity only (QQQ best,
SPY also viable)** — crypto (BTC/USDT, ETH/USDT) is decisively rejected
(0/36 cells), consistent with the strategy's premise being TradFi-specific
(traditional defensive assets like TLT/GLD have no clear economic link to
BTC/ETH forward returns). High-vol regime performance is also notably
weaker (2/24 pass) — a future loop could investigate whether crash periods
(2020 COVID, 2022 rate-hike) specifically break the defensive-momentum
signal.

## Notes

- Source: https://www.quantifiedstrategies.com/alternative-60-40-portfolio/
  (visited 2026-09-11 this iteration), citing Thomas Carlson's "Defense
  First" strategy as analyzed by Allocate Smartly.
- Distinct from 2026-09-08-147 (rejected): uses all 4 Defense-First assets
  (not just GLD), the source's own multi-period-averaged momentum
  definition, and a graded continuous weight rather than a binary gate.
- Rebalanced weekly rather than the source's monthly cadence (modest
  refinement to reduce staleness while keeping turnover low: 126 trades
  over ~7.7 years on QQQ, i.e. ~16/year).
- `check_walk_forward`'s built-in `vbt.utils.splitting.RangeSplitter` still
  raises `AttributeError` in this vectorbt install (same known issue as
  prior iterations, e.g. 2026-09-08-147's own note) — used the same manual
  4-equal-chunk date-slice fallback.
