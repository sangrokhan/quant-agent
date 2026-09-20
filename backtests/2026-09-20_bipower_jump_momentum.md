# Backtest Report: Bipower Variation Jump-Momentum Strategy

**Strategy file:** `strategies/2026-09-20_bipower_jump_momentum.py`
**Date:** 2026-09-20
**Hypothesis:** Per Barndorff-Nielsen & Shephard (2004, 2006) and
TradingView's "Bipower Jump Detector [forexobroker]" script (read this
iteration via Google SERP + the TradingView script page, browser_exec
fallback since web_search DDGS returned no results): realized variance
RV=sum(r^2) vs jump-robust bipower variation BV=(pi/2)*sum(|r_t||r_{t-1}|)
over a trailing window; standardized Jump-Z = sqrt(N)*(RV-BV)/sqrt(theta*
BV^2*0.5), theta=pi^2/4+pi-5. Source's disclosed rule: enter in the
direction of the dominant (largest-|return|) bar when Jump-Z exceeds a
significance threshold (1.96 default). Adapted long-only with a
max_hold_days time-stop and re-entry cooldown via the position-state
tracking already built into the source's own design.

First bipower-variation/jump-test strategy in this repo.

## Grid test summary (Step 6)

`z_threshold in [1.65, 1.96, 2.58]` x `max_hold_days in [5, 10, 20]`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 45, pass_fraction: 0.417
- by_asset_class: equity 21/54 passed, crypto 24/54 passed (fairly balanced)
- by_vol_regime: low 24/36, mid 18/36, **high 3/36**
- best_cell: equity/QQQ/low-vol, z_threshold=1.96/max_hold_days=5, Sharpe 2.03

Grid pass fraction (0.417) is respectable and reasonably balanced across
asset classes, but concentrated overwhelmingly in low/mid-vol regime
slices -- high-vol regime nearly fails universally (3/36).

## Single-config validators (Step 7)

Full-sample (2019-01-01 to 2026-09-01), best-performing config per symbol
across the full 3x3 param grid:

| Symbol | Best config | Sharpe | MDD | Pass? |
|---|---|---|---|---|
| QQQ | z=1.65, hold=5 | 0.724 | 0.181 | Sharpe fails |
| SPY | z=1.65, hold=5 | 0.636 | 0.102 | Sharpe fails |
| BTC/USDT | z=1.65, hold=5 | 0.576 | 0.655 | Both fail |
| ETH/USDT | z=1.65, hold=5 | 0.953 | 0.416 | Sharpe near-miss, MDD fails |

**No config on any symbol clears the full-sample Sharpe>=1.0 threshold.**
The grid's 45/108 passing cells are entirely a product of vol-regime
SLICING -- the strategy performs well in isolated low/mid-vol windows but
that edge does not survive averaging over the complete sample (the
low-vol-regime outperformance is offset by weaker/negative performance in
mid/high-vol periods within the same full series).

## Decision: REJECT

No symbol passes the full-sample Sharpe threshold at any tested parameter
combination, despite a respectable-looking grid pass_fraction (0.417) that
is driven entirely by within-sample vol-regime slicing rather than genuine
full-cycle edge. This is a useful illustration of why RESEARCH_LOOP.md Step
7's single-config full-sample validator check is necessary in addition to
the Step 6 grid -- a grid pass_fraction alone can look encouraging while
masking the fact that no single full-sample configuration is actually
tradeable end-to-end.

Consistent with the source script's own explicitly disclosed limitation:
"The Barndorff-Nielsen test was designed for high-frequency intraday
returns; on daily timeframes the diffusion-jump decomposition is harder to
interpret and BV becomes a less precise diffusion proxy" -- this repo's
daily-bar-only data appears to be exactly the regime where that limitation
bites: the jump-significance gate fires often enough to matter in the grid
slices but doesn't translate into a robust full-sample edge.
