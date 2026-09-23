# Approximate Entropy "Predictability Emergence" Collapse Trigger — Backtest Report (2026-09-24)

## Hypothesis

Per algobot.live's "Predictability Emergence Trend" strategy
(https://www.algobot.live/predictability-emergence-trend-ea-mt5/, found via
`web_search` and read in full via `browser_exec` since `web_extract`'s
configured backend is search-only): rather than a static Approximate
Entropy (ApEn) regime gate (already tested in this repo's
2026-09-08-047), this strategy fires on a FRESH entropy DOWN-CROSS event
(ApEn on z-scored closes was >=threshold on the prior bar, now <threshold)
-- the specific transition moment a noisy market organizes into a
structured move. Direction comes from a least-squares regression slope of
recent closes, confirmed by price above a baseline EMA (source's own
two-part directional confirmation). Long-only per SAFETY.md. Exit on close
crossing back below the baseline EMA or a max_hold_days time-stop
(substituting for the source's intrabar ATR-stop/trail machinery, not
representable in this repo's daily-bar generate_returns_fn contract).

Distinct from this repo's 2 prior entropy-family entries: 2026-09-08-047
(ApEn as a persistent regime *gate*, not an event trigger) and the
permutation-entropy/sample-entropy variants (different estimators
entirely). This is the first "entropy collapse EVENT" (fresh-transition,
one-shot-fire) construction in this repo.

## Strategy file

`strategies/2026-09-24_entropy_collapse_predictability_emergence.py`

## Grid test summary (Step 6)

144 cells: `entropy_threshold ∈ {0.25, 0.28, 0.30}` × `slope_window ∈ {10,
20}` × `max_hold_days ∈ {15, 30}` × symbols `{QQQ, SPY, BTC/USDT,
ETH/USDT}` × 3 vol-regime terciles, 2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | 0.347 (50/144) |
| equity pass | 30/72 |
| crypto pass | 20/72 |
| low-vol pass | 34/48 |
| mid-vol pass | 13/48 |
| high-vol pass | 3/48 |
| best cell | QQQ low-vol, entropy_threshold=0.28/slope_window=10/max_hold=15, Sharpe 2.57 |
| worst cell | ETH/USDT high-vol, entropy_threshold=0.3/slope_window=10/max_hold=15, Sharpe -0.88 |

QQQ configs cluster around 0.67 pass_fraction across most threshold/window
combos; BTC/USDT reaches 0.67 at entropy_threshold=0.28/slope_window=10
(both max_hold values); SPY and ETH/USDT weaker (mostly 0.33 or 0).

## Single-config validation (Step 7) — best config: entropy_threshold=0.28, slope_window=10, max_hold_days=15

| Validator | QQQ | SPY | BTC/USDT |
|---|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.352 | FAIL 0.377 | **PASS** 1.028 |
| Max Drawdown (<=0.25) | PASS 0.153 | PASS 0.155 | PASS 0.216 |
| TC Survival (>=0.5 net Sharpe, 10bps/trade) | PASS 1.249 | FAIL 0.270 | PASS 0.998 |
| Walk-Forward (>=0.75 pass fraction, 4 splits) | PASS 1.0 (4/4) | PASS 0.75 (3/4) | PASS 1.0 (4/4) |
| Parameter Sensitivity (<=0.5 relative std) | PASS 0.269 | PASS 0.335 | PASS 0.451 |

QQQ: 5/5 pass. BTC/USDT: 5/5 pass (param-sensitivity 0.451, closest to the
0.5 threshold but still passing). SPY: 3/5 pass, decisive Sharpe and
TC-survival fail (few, poorly-timed trades in this asset).

## Decision

**Accept for QQQ and BTC/USDT.** Reject SPY (decisive Sharpe + TC-survival
fail). Strategy file and this report kept; log entry records the QQQ +
BTC/USDT accepted scope explicitly (shared config across both symbols:
entropy_threshold=0.28, slope_window=10, max_hold_days=15).
