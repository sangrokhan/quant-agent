# Realized-Volatility Term-Structure (RV7/RV30) Regime Gate

**Hypothesis / source:** Google AI-overview synthesis (LuxAlgo sourced) via
browser_exec Google SERP fallback of a crypto RV term-structure strategy:
short-horizon realized vol (RV7) vs long-horizon (RV30), RV_ratio=RV7/RV30.
Contango (ratio<0.90) = calm regime; backwardation (ratio>1.05) = acute
stress/shock regime. Applied here as a regime gate on a simple SMA
trend-following long: hold only while trending AND in the calm/contango
regime; exit on trend break, vol-spike into backwardation, or a
max_hold_days time-stop. First REALIZED-vol (as opposed to VIX
implied-vol) term-structure strategy in this repo -- pure price-derived,
so directly testable on crypto (unlike the 4 prior VIX-based term-structure
strategies, all equity-only by construction).

**Grid summary (scripts/run_grid_rv_termstructure.py, 144 cells: 3
contango_threshold x 2 trend_window x 2 backwardation_threshold x 2 asset
classes x 2 symbols x 3 vol regimes):**
- pass_fraction: 0.2014 (29/144)
- by_asset_class: equity 29/72; **crypto 0/72 (decisive -- despite being
  purpose-built to be crypto-computable, the strategy still fails
  categorically on crypto)**
- by_vol_regime: low 24/48, mid 5/48, **high 0/48**
- best_cell: SPY, contango=0.95/trend_window=50/backwardation=1.15,
  low-vol, Sharpe 2.23
- worst_cell: QQQ, contango=0.90/trend_window=100/backwardation=1.15,
  high-vol, Sharpe -0.52

**Single-config validators (contango_threshold=0.95, trend_window=50,
backwardation_threshold=1.15, 2017-01-01 to 2026-09-01):**

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | FAIL 0.724 | FAIL 0.751 |
| Max drawdown (<=0.25) | PASS 0.242 | PASS 0.208 |
| TC survival (10bps, N trades) | PASS 0.591 (101 trades) | PASS 0.582 (96 trades) |
| Walk-forward (4 manual splits, >=0.75) | PASS 1.0 | PASS 1.0 |
| Parameter sensitivity (12-cell sweep, <=0.5) | PASS 0.073 (excellent) | PASS 0.069 (excellent) |

A wider 96-cell full-sample sweep (contango in {0.80,0.85,0.90,0.95},
trend_window in {30,50,100}, backwardation in {1.05,1.15}, max_hold_days
in {15,30,45}) found the best achievable full-sample Sharpe was still only
0.882 (QQQ) / 0.901 (SPY) -- consistently just under the 1.0 bar.

**Verdict: REJECTED (strong near-miss).** This is the cleanest near-miss
tested this cron trigger: 4 of 5 validators pass comfortably, including an
unusually STABLE parameter-sensitivity profile (relative std ~0.07 vs the
0.5 threshold -- among the lowest seen in this repo, meaning performance
barely varies across the parameter grid, a sign of a real, if modest,
edge rather than overfitting). Only Sharpe fails, and only narrowly
(0.72-0.75 vs 1.0, best achievable across an even wider sweep ~0.88-0.90).
Flagging for a future iteration to revisit with either (a) a tighter
trend/regime combination not yet tried, or (b) relaxing the max_hold_days
backstop to let winners run longer, since the strategy's stability profile
suggests refinement rather than a fundamentally broken hypothesis. Crypto
remains categorically 0/72 despite the underlying RV metric itself being
crypto-native -- the trend-following + regime-gate combination on top of
it does not transfer to crypto's price dynamics.
