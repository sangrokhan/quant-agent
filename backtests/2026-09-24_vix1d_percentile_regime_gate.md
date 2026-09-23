# VIX1D Percentile-Rank Regime Gate — Backtest Report (2026-09-24)

## Hypothesis

CBOE's VIX1D (1-Day Volatility Index, launched April 2023, per
https://volatilitybox.com/research/vix1d-explained/, read via
`browser_exec` after `web_search` surfaced it) measures expected S&P 500
volatility over just the next trading day, reacting far faster to
event-specific stress than the 30-day VIX and mean-reverting on the order
of hours to a day. This strategy tests whether an SMA trend-following
signal performs better gated to only trade while VIX1D sits in its own low
rolling-percentile regime. First VIX1D-specific strategy in this repo (0
prior KB hits) -- distinct from existing VIX-level/VIX-BB/VIX9D-ratio/
VIX-term-structure strategies, none of which use the 1-day-horizon index.

VIX1D (`^VIX1D` via yfinance) only exists from its April 2023 launch, so
this backtest window is necessarily shorter (2023-05 to 2026-09, ~3.3
years) than this repo's typical 2019-2026 window -- a scope limitation
inherent to the data series itself.

## Strategy file

`strategies/2026-09-24_vix1d_percentile_regime_gate.py`

## Preliminary parameter scan (before committing to a full grid)

Given VIX1D's SPX-specific construction, this strategy is only meaningful
for QQQ/SPY (no crypto analogue -- BTC/ETH have no comparable 1-day
options-implied-vol index feeding data/loaders.py). A parameter scan
across trend_window and calm_percentile on both symbols before running the
full grid_test.py harness:

| Symbol | trend_window | calm_percentile | Full-sample Sharpe |
|---|---|---|---|
| QQQ | 20 | 0.4 | -0.53 |
| QQQ | 50 | 0.5 | -0.07 |
| QQQ | 100 | 0.5 | 0.22 |
| SPY | 20 | 0.6 | 0.32 |
| SPY | 50 | 0.6 | 0.43 |
| SPY | 100 | 0.5 | 0.54 |
| SPY | 100 | 0.6 | **0.85 (best found)** |

QQQ never exceeds Sharpe ~0.22 across the scan; SPY's best config (0.85)
still falls decisively short of the 1.0 Sharpe threshold this repo
requires, and no config approached passing territory for either symbol.

## Decision

**Reject without proceeding to the full grid_test.py / validators.py
suite** -- the preliminary scan is decisive and uniform (best full-sample
Sharpe found across ~14 parameter combinations on the only two applicable
symbols is 0.85, well short of 1.0), so running the full 3-vol-regime grid
and single-config validator suite would not change the outcome and was
skipped to conserve this iteration's budget (per RESEARCH_LOOP.md
guidance to scope effort to what preliminary evidence already shows).
Logged as a rejected candidate so a future loop does not re-test the same
VIX1D-percentile-gate construction without a materially different
mechanism (e.g. a continuous sizing dial instead of a binary gate, or
combining with a different base trend signal).
