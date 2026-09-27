# Backtest Report: Distribution-Day Kill-Switch SPY Rescue Attempt (rejected)

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_distribution_day_killswitch_sma200.py` (unchanged)
**Hypothesis id:** 2026-09-27-052

## Hypothesis

Direct rescue attempt of this same cron trigger's near-miss 2026-09-27-002
(Distribution-Day cluster kill-switch on SMA(200) trend-following, QQQ
accepted Sharpe 1.343, SPY near-miss Sharpe 0.849 at the shared default
config `trend_window=200, down_pct=0.002, window=15, dist_threshold=6,
cooldown_days=15`). A dedicated SPY-focused full-sample parameter search
(1,280-combination sweep: `trend_window` x `down_pct` x `window` x
`dist_threshold` x `cooldown_days`) was run to find an SPY-specific
optimum.

## Parameter search results

Best full-sample Sharpe found: **1.114** at `trend_window=200,
down_pct=0.0015, window=20, dist_threshold=8, cooldown_days=20` (16
trades). All other validators pass cleanly at this config (MDD 0.141,
TC-survival net Sharpe 1.087, walk-forward 4/4 splits positive).

However, a `parameter_sensitivity` check over a 36-cell local grid
(`trend_window` in {175,200,225} x `dist_threshold` in {6,7,8,9} x
`cooldown_days` in {15,20,25}) **fails decisively**: relative_std 0.729
(threshold 0.5). Diagnosing why: holding `trend_window=200,
down_pct=0.0015, window=20, cooldown_days=20` fixed and varying only
`dist_threshold`:

| dist_threshold | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|
| Sharpe | -0.015 | -0.044 | 0.612 | **1.114** | 0.959 | 0.990 |

`dist_threshold` is a sharp CLIFF, not a broad plateau: Sharpe is
near-zero/negative at 5-6, jumps abruptly at 7-8, and partially reverts
at 9-10. The chosen "best" value of 8 sits on a narrow local spike, not a
robust plateau -- the classic fragile-single-optimum signature this
repo's convention treats as overfitting (e.g. 2026-09-21-255
HD/LOW pairs rejected on the same pattern). A separate narrower check
(varying only `trend_window`/`down_pct`, holding `dist_threshold=8`
fixed) DOES pass cleanly (relative_std 0.085), confirming the fragility
is isolated specifically to the `dist_threshold` knob, not a
generally-unstable strategy.

## Decision

**Rejected.** The best-found SPY configuration clears Sharpe/MDD/TC-
survival/walk-forward comfortably, but fails parameter sensitivity on a
sharp `dist_threshold` cliff -- this is overfitting to a specific
threshold value rather than a genuine, robust edge. QQQ (accepted via the
shared default config in 2026-09-27-002) remains the only live version of
this strategy; SPY is not pursued further this cron trigger.
