# Psychological Line (PSY) Oversold Mean Reversion

**Strategy file:** `strategies/2026-09-08_psy_line_oversold_reversion.py`
**Source:** https://www.investchannels.com/psychological-line-indicator-trading-strategies-and-tips/

## Hypothesis

The Psychological Line (PSY) is a sentiment oscillator: percentage of the
last N bars closing higher than the prior close (0-100 scale, counting
up/down bars, not weighting by move magnitude like RSI/Stochastic).
Oversold readings (<30) are said to precede upward reversals. Test:
long entry when PSY drops below an oversold threshold, exit when PSY
reverts back above a midline (50/60) or a time-stop.

## Grid test summary (Step 6)

`param_grid`: `psy_period in {8,12,20}`, `oversold_threshold in {20,30}`,
`exit_threshold in {50,60}`; `vol_regime_splits=3`; symbols: equity
QQQ/SPY, crypto BTC/USDT/ETH/USDT.

| asset_class | pass_fraction | low-vol | mid-vol | high-vol |
|---|---|---|---|---|
| equity (QQQ/SPY) | 11/72 (0.153) | 5/48 | 0/48 | 6/48 |
| crypto (BTC/ETH) | 0/72 (0.0) | 0/48 | 0/48 | 0/48 |

Overall pass_fraction 11/144 (0.076) — weak and inconsistent (passes
spread thinly across low AND high vol but not mid, no coherent regime
story). Best cell Sharpe 1.62 (QQQ, high-vol, psy_period=8) is an isolated
spike, not representative of the grid as a whole. Crypto rejected
decisively across all 72 cells.

## Decision: **REJECTED** (decisive — did not proceed to single-config validators)

Given the grid's own weak and inconsistent pass_fraction (0.076 overall,
no full-sample-passing candidate visible from the pattern, no coherent
by-vol-regime story to exploit with a regime gate the way several other
near-misses this cron trigger had), this does not warrant spending
compute on the full Step 7 validator suite — the grid itself already
rules the idea out per RESEARCH_LOOP.md Step 6/8 guidance (a grid can be
the sole basis for rejection when its own summary is decisively weak).

**Notes for future iterations:** the pure up/down-bar-count formulation of
PSY appears to carry materially less signal than magnitude-weighted
oscillators (RSI, Stochastic) already tested in this repo — likely
because it discards information about the SIZE of each day's move, only
its sign. Not worth revisiting with different threshold/period
combinations; consider this indicator closed unless combined with a
magnitude-based confirmation filter in a future iteration.
