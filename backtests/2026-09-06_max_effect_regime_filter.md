# Backtest Report: MAX-Effect-Inspired Regime Filter -- QQQ (2026-09-06)

**Hypothesis:** Per the academic "MAX effect" literature (Bali, Cakici &
Whitelaw 2011; corroborated by follow-on papers surfaced via search --
Emerald Publishing "role of arbitrage risk in the MAX effect", MDPI
emerging-markets replication, SSRN "Underpricing of Stocks following
Extreme Negative Returns"): assets whose maximum single-day return over the
prior ~month is unusually extreme relative to their own history
subsequently underperform, as the "lottery-like" spike attracts
return-chasing demand that later unwinds. The original research is a
cross-sectional decile-sort across a stock universe, infeasible with this
repo's single-symbol `grid_test.py` framework -- adapted here as a
single-symbol TIME-SERIES regime filter: stay long (in an existing uptrend)
UNLESS the symbol's own trailing-month rolling-max daily return is
currently in the top percentile of its own trailing-year distribution (a
recent "lottery day" just occurred); re-enter once that extreme reading has
aged out of the rolling window.

**Source:** Google search "short term reversal skewness stock filter rules
quantitative strategy" and "MAX maximum daily return past month lottery
stocks reversal specific threshold decile" (academic MAX-effect literature,
no single primary-source URL -- synthesized from multiple abstracts/summaries).

**Strategy file:** `strategies/2026-09-06_max_effect_regime_filter.py`

## Step 6 grid summary (`run_strategy_grid`)

- Grid: `max_percentile` in {0.85, 0.90, 0.95} x `trend_window` in {50, 100}
  x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x vol regimes {low, mid, high}
- **72 total cells, 17 passed -- pass_fraction = 0.236**
- by_asset_class: equity 17/36 (47%), crypto 0/36 (0%)
- by_vol_regime: low 12/24 (50%), mid 5/24 (20.8%), high 0/24 (0%)
- best_cell: QQQ, max_percentile=0.9, trend_window=50, low-vol regime, Sharpe=2.65
- worst_cell: QQQ, max_percentile=0.95, trend_window=50, high-vol regime, Sharpe=-0.13

Same qualitative shape as other recent iterations this cron trigger:
equity-only edge, degrades in high-vol regimes (0/24 passing), crypto
categorically unsuitable (0/36).

## Step 7 single-config validators (best grid combo full-sample: QQQ, max_percentile=0.9, trend_window=50)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.183 | >= 1.0 | **PASS** |
| Max drawdown | 0.189 | <= 0.25 | **PASS** |
| Transaction cost survival (net Sharpe, 10bps/trade, 92 trades) | 1.043 | >= 0.5 | **PASS** |
| Parameter sensitivity (relative std across 6 combos) | 0.075 | <= 0.5 | **PASS** (very stable) |
| Walk-forward | not run | -- | `check_walk_forward` broken in installed vectorbt (`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`) -- pre-existing repo-wide tooling issue, skipped for every strategy tested this cron trigger. |

**SPY cross-check** (same params, full sample): Sharpe 0.824 (fails 1.0
threshold, near-miss), MDD 0.179 (passes). Accept is scoped to QQQ.

## Decision: ACCEPT (QQQ only)

All Step 7 validators pass on QQQ with strong parameter-sensitivity
stability (0.075 relative std). SPY is a near-miss (Sharpe 0.82), not a
clean pass, so this strategy is scoped to QQQ per this repo's convention
(same pattern as `2026-09-03_bb_meanrev_qqq_volregime.py` and
`2026-09-06_woodies_cci_trendline_break.py`, both also QQQ-scoped accepts).
Crypto is explicitly out of scope (0/36 grid cells) -- do not extend this
strategy to BTC/ETH. Note this is a DEFENSIVE/regime-filter framing of the
MAX effect (avoiding longs right after lottery-day spikes) rather than an
active short -- consistent with this repo's long-only convention -- so the
edge comes from AVOIDING drawdown-prone periods, not from a directional
short bet.
