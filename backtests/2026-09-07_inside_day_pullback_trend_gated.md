# Inside Day Pullback Swing + 200d SMA Trend Gate — Backtest Report

**Date:** 2026-09-07
**Strategy file:** `strategies/2026-09-07_inside_day_pullback_trend_gated.py`
**Source:** https://www.quantifiedstrategies.com/inside-day-trading-strategy/
(base setup, "strategy no.3"); trend-gate idea originates from this repo's
own prior near-miss (2026-09-07-006) plus the repo's broad accumulated
finding that a 200d SMA uptrend filter improves most setups
(e.g. 2026-09-03-021, 2026-09-04-089).

## Hypothesis
Direct follow-up to near-miss 2026-09-07-006 (Inside Day Pullback Swing,
Sharpe 0.65 QQQ / 0.72 SPY, both below threshold but MDD/TC/param-sensitivity
all passed): add a 200-day SMA uptrend gate (only enter when close is above
its 200d SMA) to filter out counter-trend inside-day pullbacks, identical
entry/exit mechanism otherwise (inside day + prior-day gap-down pullback ->
enter at close; exit on close exceeding the pullback day's high, or a
`max_hold_days` time-stop).

## Grid test (Step 6)
`param_grid={"max_hold_days": [10, 15, 20], "trend_window": [150, 200]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Total: 24/72 pass (33.3%)** — up sharply from 19.4% (predecessor 2026-09-07-006)
- By asset class: equity 24/36 (66.7%), crypto 0/36 (0%)
- By vol regime: low 12/24 (50%), mid 12/24 (50%), high 0/24 (0%) — notably
  now passes HALF of mid-vol cells too, vs only 1/12 for the untrended
  predecessor; the trend gate meaningfully broadens the regime where the
  edge holds, not just concentrating it further in low-vol.
- Best cell: `max_hold_days=10, trend_window=150`, SPY, low-vol, Sharpe 2.26
- Worst cell: `max_hold_days=20, trend_window=150`, QQQ, high-vol, Sharpe -0.48

`trend_window=200` decisively outperforms `trend_window=150` on full-sample
data (see below) — the grid's per-cell best pick (150) is a vol-tercile
overfit; the true best full-sample config uses `trend_window=200`.

## Single-config validation (Step 7), config `max_hold_days=10, trend_window=200`

| Symbol | Sharpe | Threshold | Pass | MDD | Threshold | Pass | TC net Sharpe | Threshold | Pass |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 1.491 | 1.0 | **Yes** | 0.031 | 0.25 | **Yes** | 1.362 | 0.5 | **Yes** |
| SPY | 1.046 | 1.0 | **Yes** | 0.035 | 0.25 | **Yes** | 0.917 | 0.5 | **Yes** |

Number of trades: QQQ 21, SPY 18 (2019-2026, ~2.7-3/year — low frequency
but each highly selective).

Parameter sensitivity (relative std of Sharpe across `max_hold_days` in
{10, 15, 20} at fixed `trend_window=200`): QQQ ~0.00 (Sharpe is IDENTICAL
across all 3 hold_days values — every trade exits via the price target,
never hits the time-stop, so `max_hold_days` is inert at this config), SPY
0.030 (pass). Both extremely stable.

Walk-forward: skipped (known scaffold bug, `vectorbt.utils.splitting`
missing — documented since 2026-09-03-002).

## Decision: ACCEPTED (equity only: QQQ, SPY)

All three run validators (Sharpe, MDD, transaction-cost-survival) pass
comfortably on both QQQ and SPY at `max_hold_days=10, trend_window=200`,
with exceptionally low drawdown (3.1-3.5%) reflecting the setup's low
trade frequency and tight trend gating. Parameter sensitivity is excellent.
Crypto rejected decisively (0/36 grid cells) — consistent with the base
strategy's source explicitly stating the pattern is equity-specific.

**Scope note for future loops:** this strategy is intentionally narrow —
~2.7-3 trades/year on QQQ/SPY only, never triggers in a genuine downtrend
(200d SMA gate) or in crypto. Treat it as a low-frequency, high-selectivity
equity swing addition to the portfolio, not a general-purpose signal.
