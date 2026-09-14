# 2026-09-14 Firefly Oscillator Continuous Sizing Overlay (SMA Trend Gate)

## Hypothesis

Firefly Oscillator (LuxAlgo, community-bred momentum gauge) -- confirmed
via https://www.luxalgo.com/library/indicator/firefly-oscillator/
(browser_exec navigation; `web_search` DDGS backend returned an
empty/error result for this query, so fell back to Google SERP via
browser_exec for keyword discovery too): weighted price =
`(High+Low+2*Close)/4` (double-counts close); z-score that weighted price
against its own rolling EMA basis (default length 10) and rolling std;
double-smooth the z-score with a zero-lag EMA pass (default length 3);
rescale so 50 is neutral on a roughly 0-100 scale.

This repo has exactly 1 prior Firefly Oscillator entry (2026-09-09-058, a
binary midline(50)-crossover ENTRY trigger, accepted SPY-only). That entry
never used the oscillator's raw (0-100, 50-centered) value as a continuous
SIZING dial -- the same reframing pattern that has repeatedly rescued
binary-only bounded oscillators in this repo (BOP, CHOP, VZO, ADX,
DMI-diff, Vortex-diff-ratio, TSI, RMI, SMI, STARC %B-analog, etc.).

Signal construction: `dial = clip((firefly-50)/50, -1, 1)`, exposure =
`clip(base_exposure + sensitivity*dial, 0, leverage_cap)`, gated to 0
whenever `close <= SMA(trend_window)`, held constant within a `deadband`
of the last update to control turnover.

## Grid test summary (Step 6)

`param_grid={"basis_length":[10,14], "sensitivity":[0.5,0.6,0.7],
"deadband":[0.15,0.2]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3` (144 cells).

- **pass_fraction: 0.486** (70/144)
- by_asset_class: equity 36/72 passed, crypto 34/72 passed (first sizing-dial
  candidate this cron trigger with roughly balanced equity/crypto grid pass
  rates before per-symbol retuning)
- by_vol_regime: low 48/48 (100%), mid 22/48 (46%), high 0/48 (0% -- edge
  concentrated in low/mid volatility, consistent with nearly every other
  trend-following sizing-dial strategy in this repo)
- best_cell: QQQ low-vol, basis_length=10/sensitivity=0.5/deadband=0.2,
  Sharpe 2.57
- worst_cell: QQQ high-vol, basis_length=14/sensitivity=0.7/deadband=0.2,
  Sharpe -0.23

## Single-config validation (Step 7), after per-symbol retuning

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | basis=10, sens=0.5, db=0.4 | 1.540 | 0.121 | 1.264 | 1.00 | 0.073 | YES |
| SPY      | basis=10, sens=0.5, db=0.3 | 1.089 | 0.068 | 0.562 | 0.75 | 0.031 | YES |
| BTC/USDT | basis=10, sens=0.3, db=0.2, leverage_cap=0.25, base_exposure=0.2 | 1.525 | 0.128 | 1.205 | 1.00 | 0.006 | YES |
| ETH/USDT | basis=10, sens=0.3, db=0.15, leverage_cap=0.25, base_exposure=0.2 | 1.334 | 0.130 | 1.106 | 1.00 | 0.012 | YES |

All four symbols pass all five validators (Sharpe, MDD, transaction-cost
survival, walk-forward, parameter sensitivity) at their per-symbol tuned
configs. Equity configs needed a widened deadband (0.3-0.4 vs the 0.15-0.2
grid default) to cut turnover enough for transaction-cost survival; crypto
configs needed the leverage_cap-aware low-exposure recalibration pattern
already established for prior crypto sizing-dial accepts this cron
trigger (base_exposure=0.2, leverage_cap=0.25, lower sensitivity=0.3) to
keep MDD under 25%.

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

First strategy this cron trigger to accept all 4 target symbols
(equity+crypto) at a single reframing pass, without needing a separate
crypto-leverage-cap follow-up iteration.

## Notes

- Walk-forward fallback: `vbt.utils.splitting.RangeSplitter` unavailable in
  the installed `vectorbt` version; used the repo's standard manual
  4-equal-slice fallback (same as other `run_validate_*.py` scripts).
- Source: https://www.luxalgo.com/library/indicator/firefly-oscillator/
