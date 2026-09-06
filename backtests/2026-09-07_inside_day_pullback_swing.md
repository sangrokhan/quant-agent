# Inside Day Pullback Swing — Backtest Report

**Date:** 2026-09-07
**Strategy file:** `strategies/2026-09-07_inside_day_pullback_swing.py`
**Source:** https://www.quantifiedstrategies.com/inside-day-trading-strategy/
("Inside day trading strategy no.3: A swing trade" — fully disclosed rule,
non-paywalled; source's own S&P 500 backtest since 1993: 89 trades,
avg gain 0.45%/trade, profit factor 2.1, explicitly "only works in the
equity markets... works opposite in gold")

## Hypothesis
(1) Today is an inside day (high<yesterday's high AND low>yesterday's
low); (2) yesterday's high was below the close two days prior (a gap-down
pullback). If both hold, enter long at today's close; exit when a later
close exceeds yesterday's high (the pullback day's high), or a
`max_hold_days` safety time-stop (source's rule has no explicit time-stop;
added per this repo's standard practice).

## Grid test (Step 6)
`param_grid={"max_hold_days": [10, 15, 20]}`, symbols
`{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Total: 7/36 pass (19.4%)**
- By asset class: equity 7/18 (38.9%), crypto 0/18 (0%)
- By vol regime: low 6/12 (50%), mid 1/12 (8.3%), high 0/12 (0%)
- Best cell: `max_hold_days=10`, SPY, low-vol, Sharpe 2.46
- Worst cell: `max_hold_days=20`, ETH/USDT, high-vol, Sharpe -0.17

## Single-config validation (Step 7), best grid config `max_hold_days=10`

| Symbol | Sharpe | Threshold | Pass | MDD | Threshold | Pass | TC net Sharpe | Threshold | Pass |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 0.651 | 1.0 | No | 0.164 | 0.25 | Yes | 0.575 | 0.5 | Yes |
| SPY | 0.716 | 1.0 | No | 0.096 | 0.25 | Yes | 0.647 | 0.5 | Yes |

Parameter sensitivity (relative std of Sharpe across `max_hold_days` in
{10, 15, 20}): QQQ 0.023 (pass), SPY 0.064 (pass) — extremely stable,
among the most parameter-insensitive strategies tested in this repo.

Walk-forward: skipped (known scaffold bug, `vectorbt.utils.splitting`
missing — documented since 2026-09-03-002).

## Decision: REJECTED (clean near-miss)

MDD, transaction-cost-survival, and parameter-sensitivity ALL pass
comfortably on both QQQ and SPY. Only the Sharpe ratio falls short
(0.65 QQQ / 0.72 SPY vs 1.0 threshold) — a real but insufficient
risk-adjusted edge, not a decisive failure. This confirms the source
article's own finding that a modest, low-frequency (25-30 trades over
7.7 years) equity-only edge exists but is too weak to clear this repo's
Sharpe bar as a standalone strategy. Crypto fails decisively (0/18 grid
cells), consistent with the source's own statement that the pattern
"works opposite in gold" — i.e. is not a universal microstructure effect.

**Future revisit idea:** this is a genuine near-miss with excellent
MDD/TC/param-stability — a plausible next step is adding a trend filter
(e.g. only take the setup when price is above its 200d SMA, this repo's
most common successful gate) to see if filtering out counter-trend
inside-day pullbacks lifts the Sharpe over 1.0 without sacrificing the
strategy's very low drawdown/parameter-instability profile.
