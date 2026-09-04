# Klinger Volume Oscillator (KVO) Signal-Line Crossover + EMA Trend Filter — Backtest Report

**Date:** 2026-09-04
**Strategy file:** `strategies/2026-09-04_klinger_volume_oscillator_crossover.py`
**Outcome:** REJECTED (near-miss on transaction costs)

## Hypothesis

Per Google's AI-overview summary of LightningChart/EnlightenedStockTrading
sources: Stephen Klinger's Volume Oscillator (KVO) — EMA-difference of a
volume-force term derived from H/L/C trend direction and volume, further
smoothed with a signal-line EMA — gives a long entry when the KVO line
crosses above its signal line, confirmed by a 50-period EMA trend filter;
exit when KVO crosses back below the signal line or price drops below the
EMA. First KVO strategy tested in this repo (distinct from OBV -027,
CMF, MFI, VWMA -060 — all differently-constructed volume indicators).

Source: Google AI-overview + LightningChart/EnlightenedStockTrading search
snippets (found via `browser_exec` after `web_search` failed with a
DDGS/Yahoo TLS connection error on this query). quantifiedstrategies.com's
own Klinger article snippet (CAGR 5.09% vs. buy-hold 7.46%) suggested a
weak edge but was not opened directly.

## Grid test summary (fast_span x slow_span x ema_window, 2 equity + 2
crypto symbols, 3 vol regimes)

- total_cells: 96, passed_cells: 28, **pass_fraction: 0.292**
- by_asset_class: equity 28/48, crypto **0/48**
- by_vol_regime: low 16/32, mid 9/32, high 3/32
- best_cell: QQQ, fast_span=34/slow_span=55/ema_window=50, low-vol regime,
  Sharpe 1.79

## Full-sample Sharpe by config (equity only, search over fast/slow/signal/ema)

Best found: SPY, fast_span=21/slow_span=45/signal_span=13/ema_window=100,
**Sharpe 1.111** (passes 1.0 threshold). QQQ same config: Sharpe 0.875.

## Single-config validators (primary config: SPY, fast_span=21,
slow_span=45, signal_span=13, ema_window=100)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | pass | 1.111 | 1.0 |
| max_drawdown | pass | 0.149 | 0.25 |
| transaction_cost_survival | **FAIL** | 0.199 (net Sharpe after costs) | 0.5 |

350 round-trip trades over 7.7yr — very high frequency for a daily-bar
strategy (roughly 45 trades/year). At 10bps/trade the cost drag (~3.5%
cumulative) knocks the passing gross Sharpe (1.111) down to a failing net
Sharpe (0.199). Attempts to reduce trade frequency by widening
signal_span (13->21->34) or ema_window lowered Sharpe below 1.0 instead
(e.g. signal_span=21 -> Sharpe 0.785), so no config found simultaneously
clears both Sharpe and transaction-cost-survival thresholds.

## Decision

**Rejected — but a genuine near-miss, not a decisive failure.** Unlike
most rejections in this repo, the raw signal quality here is real (Sharpe
>1.0 achievable, MDD well within bounds, positive-pass equity-only grid
fraction 0.292) — the strategy fails specifically because the KVO/signal
crossover fires too frequently on daily bars, and every attempt to reduce
trade frequency (smoothing) degraded the raw Sharpe faster than it reduced
costs. Crypto rejected decisively (0/48 grid cells). Not implemented as a
live strategy, but flagged as the most promising rejected-for-fixable-
reason candidate this session: a future loop could add an explicit
minimum-holding-period gate (e.g. ignore exit signals for the first N
days after entry) to cut trade count without needing to blunt the raw
signal via extra smoothing.
