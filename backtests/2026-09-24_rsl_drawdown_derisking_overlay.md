# RSL Signal-Line Crossover with Drawdown-Based De-Risking Overlay (SPY Rescue Attempt)

**Strategy file:** `strategies/2026-09-24_rsl_drawdown_derisking_overlay.py`
**Date:** 2026-09-24
**Source:** https://quantmemo.com/concepts/drawdown-based-derisking-triggers

## Hypothesis

Rescue attempt for this same cron trigger's SPY near-miss
(2026-09-24-001: RSL signal-line crossover trend-gate, SPY Sharpe 0.710
fails 1.0 threshold, all other validators pass). Per QuantMemo's
drawdown-based de-risking-triggers concept, wrap the base RSL signal in a
tiered exposure-cut overlay (cut to X% at tier1 drawdown, flat at tier2
drawdown, hysteresis-based recovery) to see if capping losses during the
worst drawdown episodes lifts risk-adjusted return above threshold.

## Result

Swept `tier1_dd_pct` in {0.02,...,0.12}, `tier1_exposure` in {0.0,0.3,0.5,0.7},
`tier2_dd_pct` in {0.06,...,0.22} on SPY (2018-2026). Best Sharpe found across
the entire sweep was **identical to the unmodified baseline (0.7098)** at
loose thresholds (tier1=0.08, since SPY's baseline drawdown for this
strategy, 0.076, never crosses that trigger -- the overlay simply never
fires). At tighter, more aggressive thresholds that DO fire, Sharpe
actually **declines slightly** (0.671 at tier1=0.04) because cutting
exposure during small, normal drawdowns removes upside from the subsequent
recovery without meaningfully reducing risk (SPY's RSL strategy already
has very low MDD, 7.6%, well within "normal" bounds -- there is no
outsized tail-drawdown episode for a de-risking trigger to usefully cut).

## Decision (Step 8)

**Rejected — overlay does not rescue the SPY near-miss.** The de-risking
trigger mechanism is a poor fit here: SPY's RSL strategy already has a low
baseline MDD (7.6%, well under the 25% budget), so there is no outsized
drawdown episode for tiered de-risking to usefully cut -- the underlying
Sharpe shortfall (0.71 vs 1.0) is a return-generation issue, not a
tail-risk-control issue, and this class of overlay cannot fix that. The
original 2026-09-24-001 entry stands as-is (QQQ accepted, SPY rejected).
