# Cypher Harmonic Pattern (X-A-B-C-D Fibonacci Reversal) — Backtest Report (2026-09-24)

## Hypothesis

Per TradingView's Cypher-pattern documentation and arongroups.co's "Cypher
Pattern Guide: Rules, Ratios & Strategy" (both surfaced via a Google
AI-overview synthesis after `web_search` returned no results for this
query; `browser_exec` fallback used per RESEARCH_LOOP.md Step 2): the
Cypher harmonic pattern is a 5-point (X, A, B, C, D) / 4-leg reversal
pattern with precise Fibonacci ratio rules — B retraces XA 38.2%-61.8%; C
extends 113%-141.4% of XA (measured from X); D (the Potential Reversal
Zone) sits at the 78.6% retracement of the XC leg. Entry at D completion,
stop below X, target at A. First Cypher-pattern strategy in this repo (0
prior "Cypher" hits; distinct from existing Gartley/Bat/Butterfly harmonic
patterns' different ratio bands).

Swing points (X, A, B, C) are detected via fractal pivots over a rolling
`swing_window`; D is a derived (not observed) PRZ level that price must
subsequently touch to trigger entry.

## Strategy file

`strategies/2026-09-24_cypher_harmonic_pattern.py`

## Grid test summary (Step 6)

72 cells: `swing_window ∈ {2, 3, 5}` × `d_tolerance ∈ {0.03, 0.05}` ×
symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime terciles,
2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | **0.139 (10/72) — decisively weak** |
| equity pass | 5/36 |
| crypto pass | 5/36 |
| low-vol pass | 0/24 (zero) |
| mid-vol pass | 5/24 |
| high-vol pass | 5/24 |
| best cell | QQQ high-vol, swing_window=2/d_tolerance=0.03, Sharpe 1.53 |
| worst cell | SPY low-vol, swing_window=3/d_tolerance=0.05, Sharpe -1.63 |

Every single config tops out at 0.33 pass_fraction (1 of 3 vol regimes) —
no config passes 2 or more vol regimes for any symbol. Trade counts are
extremely sparse (2-10 trades over the full 2019-2026 sample per config),
a structural consequence of requiring 4 alternating swing pivots to
satisfy 3 simultaneous tight Fibonacci-ratio windows.

## Decision

**Reject across all symbols and asset classes** — the grid result is
decisive and uniform (no config anywhere reaches even a 2/3 vol-regime
pass), so the single-config validator suite (Step 7) was skipped as
uninformative given this outcome (per RESEARCH_LOOP.md Step 6/8 guidance
to scope effort to what the grid already shows). Root cause: the
triple-simultaneous Fibonacci-ratio requirement (B retrace + C extension +
D retrace) on programmatically-detected fractal pivots is far too
restrictive for daily-bar OHLCV data, producing too few trades for
statistical reliability in either direction.
