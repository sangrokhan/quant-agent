# Backtest Report: StashAway Double-Smoothed Trend Z-Score Regime (REJECTED)

**Strategy file:** `strategies/2026-09-27_stashaway_double_smoothed_zscore_regime.py`
**Hypothesis ID:** 2026-09-27-094 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

Per Tai/Leung/Jimenez, "Dynamic Factor Allocation via Momentum-Based Regime
Switching" (SSRN abstract_id=6224058, read via `browser_exec` — the PDF
itself is paywalled, but the abstract + Google AI-overview synthesis of the
SSRN listing disclose the model's shape): the paper's regime signal is
built from a trend estimate, z-score NORMALIZED, and the z-score itself
SMOOTHED a second time — "the smoothing lengths for trend estimation and
z-score smoothing" are the model's only 2 tunable hyperparameters. Bull
regime = smoothed z-score > 0. The paper's own application is cross-
sectional multi-factor allocation (feasibility-blocked for this repo's
single-symbol architecture), so only the underlying double-smoothed
regime-detection MECHANISM was tested here as a single-asset long/flat
timer, distinct from every prior z-score/trend-gate strategy in this repo
(all of which either z-score the raw price/indicator directly, or smooth
the trend, but never smooth the z-score a second time).

## Grid-test summary (Step 6)

Grid: `trend_window ∈ {30,60,90}`, `zscore_smooth_window ∈ {10,20,30}` ×
symbols `{QQQ,SPY}` (equity), `{BTC/USDT,ETH/USDT}` (crypto) ×
vol_regime_splits=3, using `validation/grid_test.py::run_strategy_grid`.

- **Overall pass_fraction: 0.287** (31/108 cells) — the highest grid
  pass_fraction of this cron trigger's iterations so far.
- **By asset class:** equity 29/54 (0.537); crypto 2/54 (0.037).
- **By vol regime:** low 20/36 (0.556); mid 11/36 (0.306); high 0/36
  (0.00) — same universal high-vol-regime failure pattern as this cron
  trigger's other constructions.
- **Best cell:** equity SPY, low-vol, `trend_window=30,
  zscore_smooth_window=10`, Sharpe 2.128.

## Full-sample single-symbol sweep (outside formal grid, wider search)

Swept `trend_window ∈ {20,30,40,60,90,120}` × `zscore_smooth_window ∈
{5,10,15,20,30}` × `zscore_lookback ∈ {126,180,252,378}` on QQQ and SPY
full sample (2015-01-01 to 2026-09-01):

- **QQQ best:** Sharpe 0.936 (below 1.0), MDD 0.286 (above 0.25) at
  `trend_window=90, zscore_smooth_window=30`.
- **SPY best:** Sharpe 0.862 (below 1.0), MDD 0.208 (passes) at
  `trend_window=30, zscore_smooth_window=10`.
- **No config (0 of 120 combinations tested) clears both Sharpe>=1.0 AND
  MDD<=0.25 simultaneously** on either symbol full-sample, despite the
  strong sub-period grid pass fraction — the strategy's edge is
  concentrated in specific low/mid-vol sub-periods rather than holding up
  consistently across the full 2015-2026 sample.

## Decision

**Reject** — despite the highest grid pass_fraction seen this cron
trigger (0.287), no full-sample QQQ or SPY config clears both validator
thresholds simultaneously. The double-smoothed z-score regime signal shows
genuine promise in sub-period slices (explaining the decent grid
pass_fraction) but does not generalize to a single full-sample config that
an investor could actually hold continuously — a future loop could
investigate whether a per-period parameter-adaptive version (rather than
one fixed trend_window/zscore_smooth_window pair for the whole sample)
resolves this gap, though that would be a materially different
(walk-forward-optimized) construction from what was tested here.
