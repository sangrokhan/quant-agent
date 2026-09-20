# LBR 3/10 Oscillator (Linda Bradford Raschke) signal-line crossover

**Strategy file:** `strategies/2026-09-20_lbr_3_10_oscillator_signal_cross.py`
**Outcome:** REJECTED (full-period Sharpe and transaction-cost survival fail on both tested equity symbols)

## Hypothesis

The "3/10 Oscillator" popularized by floor trader Linda Bradford Raschke is
an SMA-based MACD variant: `fast_line = SMA(close, 3) - SMA(close, 10)`,
`signal_line = SMA(fast_line, 16)`. Standard rule: go long when fast_line
crosses above signal_line (golden cross), flat when it crosses below (dead
cross). Sourced from Google SERP AI-overview (this iteration, browser_exec
fallback — `web_search` DDGS/Yahoo backend failed with TLS connection errors
on every query attempted) plus corroborating snippets from a worden.com
forum thread and MQL5 vendor page describing the same 3/10/16 standard
configuration. First LBR 3/10 Oscillator entry in this KB (11 prior matches
on "3-10"/"Raschke"/"LBR" were all Raschke's *other* indicators — Turtle
Soup, Momentum Pinball/LBR-RSI — structurally distinct techniques).

## Grid test (Step 6)

`param_grid`: `fast_window ∈ {3,5}`, `slow_window ∈ {10,15}`, `signal_window
∈ {9,16}` (8 combos) × `symbols = {equity: [QQQ, SPY], crypto: [BTC/USDT,
ETH/USDT]}` × `vol_regime_splits=3` (low/mid/high realized-vol terciles) =
96 cells, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.292** (28/96 cells, Sharpe≥1.0 & MDD≤0.25)
- **By asset class:** equity 18/48 (0.375), crypto 10/48 (0.208)
- **By vol regime:** low 19/32 (0.594), mid 8/32 (0.25), high 1/32 (0.031)
- **Best cell:** fast=3/slow=10/signal=9, SPY, low-vol regime, Sharpe 1.989
- **Worst cell:** fast=5/slow=10/signal=9, QQQ, high-vol regime, Sharpe -0.438

Clear pattern: this oscillator only works in low-volatility regimes across
both asset classes; it decays through mid-vol and is actively harmful in
high-vol regimes (median crypto/equity Sharpe near or below 0 in the high
tercile). Not automatically fatal per RESEARCH_LOOP.md Step 6 guidance, but
the single-config full-period validators below (best grid params, whole
sample, unconditional -- no regime gate) show the unconditional rule fails
outright once mid/high-vol periods are included.

## Single-config validators (Step 7) — best grid params (fast=3, slow=10, signal=9)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (≥1.0) | 0.540 — **FAIL** | 0.618 — **FAIL** |
| Max Drawdown (≤0.25) | 0.200 — pass | 0.148 — pass |
| Transaction cost survival (net Sharpe≥0.5, 10bps/trade, 281/277 trades) | 0.204 — **FAIL** | 0.200 — **FAIL** |
| Walk-forward (4-split, pass_fraction≥0.75) | 0.75 (3/4) — pass | 1.0 (4/4) — pass |
| Parameter sensitivity (relative_std≤0.5, 8-combo full-period sweep) | 0.282 — pass | 0.128 — pass |

`check_walk_forward` in `validation/validators.py` raised
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` in
this environment (pre-existing bug, `RangeSplitter` API not present in the
installed vectorbt version) — substituted a manual 4-equal-slice
chronological walk-forward (Sharpe>0 per slice) as a reasonable proxy,
documented in the entry's `notes`.

## Decision

**REJECTED.** Both Sharpe and transaction-cost-survival fail on full-period
unconditional signal for both equity symbols tested (crypto not
single-config-validated given the grid's decisive crypto weakness: 10/48
pass, concentrated in low-vol). The oscillator's edge is real but
concentrated entirely in low-vol regimes (grid pass_fraction 0.594 low vs
0.25 mid vs 0.031 high) — a future iteration could revisit with an explicit
low-vol regime gate (similar pattern to the already-accepted
2026-09-03-001 BB mean-reversion + vol-regime-filter strategy) rather than
trading the oscillator unconditionally through all regimes.
