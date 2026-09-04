# KVO Crossover + EMA Trend Filter + Minimum-Holding-Period Whipsaw Filter — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_kvo_crossover_minhold.py`
**Outcome:** ACCEPTED (SPY only)

## Hypothesis

Direct follow-up to the documented near-miss 2026-09-04-084 (Klinger
Volume Oscillator signal-line crossover + EMA trend filter): that
strategy had a genuinely good raw signal (equity grid pass_fraction
0.292, primary-config Sharpe 1.111) but failed transaction-cost-survival
because of high trade frequency (350 round-trips/7.7yr), and every
attempt to fix it via additional EMA smoothing degraded the signal faster
than it cut costs. Per general whipsaw-reduction guidance (minimum
separation between crossover signals is a standard technique distinct
from smoothing), this variant adds an explicit `min_hold_days` gate:
once in a position, exit signals are ignored for the first N days,
directly cutting trade COUNT without touching the oscillator's raw
sensitivity.

Source: same as -084 (Google AI-overview/LightningChart/
EnlightenedStockTrading for the base KVO rule) plus general minimum-
holding-period whipsaw-filter guidance (tradinggenie.ai/quantt.co.uk
search snippets, `web_search` failed with a DDGS/Yahoo TLS connection
error, fell back to `browser_exec`).

## Grid test summary (min_hold_days x ema_window, 2 equity + 2 crypto
symbols, 3 vol regimes)

- total_cells: 72, passed_cells: 17, **pass_fraction: 0.236**
- by_asset_class: equity 17/36, crypto **0/36**
- by_vol_regime: low 11/24, mid 4/24, high 2/24
- best_cell: SPY, min_hold_days=20/ema_window=50, low-vol regime, Sharpe
  2.34

## Single-config validators (primary config: SPY, fast_span=21,
slow_span=45, signal_span=13, ema_window=100, min_hold_days=5)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | pass | 1.388 | 1.0 |
| max_drawdown | pass | 0.109 | 0.25 |
| transaction_cost_survival | pass | 0.802 (net Sharpe after costs) | 0.5 |
| walk_forward | pass | 4/4 splits positive (1.72, 0.62, 1.20, 0.54) | 0.75 (manual date-slice, 4 splits) |
| parameter_sensitivity | pass | 0.158 (std/mean across min_hold_days 3/5/7/10/15) | 0.5 |

217 round-trip trades over 7.7yr (down from 350 in the unfiltered
version) — the min_hold_days=5 gate cut trade count by ~38% while
*raising* the gross Sharpe (1.111 -> 1.388), confirming the hypothesis
that the extra crossovers being suppressed were net-negative whipsaws
rather than genuine signal.

QQQ at the same shared config: Sharpe 0.653 (fails), MDD 0.171 (passes) —
a clear miss, not a near-miss; QQQ not accepted.

## Decision

**Accepted (SPY only, fast_span=21/slow_span=45/signal_span=13/
ema_window=100/min_hold_days=5).** All five validators pass, including a
perfect 4/4 walk-forward split and low parameter sensitivity. This
directly validates the hypothesis from the prior iteration's near-miss:
the minimum-holding-period whipsaw filter fixed the transaction-cost
problem without degrading signal quality, unlike the smoothing-based
attempts in -084. QQQ rejected at the shared config (Sharpe 0.653, clear
miss). Crypto rejected decisively (0/36 grid cells). This is the first
case in this repo of an explicitly targeted fix converting a documented
near-miss into a clean accept within the very next iteration.
