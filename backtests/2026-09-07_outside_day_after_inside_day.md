# Outside Day After Inside Day (HHLL-style) — Backtest Report

**Date:** 2026-09-07
**Strategy file:** `strategies/2026-09-07_outside_day_after_inside_day.py`
**Source:** QuantifiedStrategies.com's own DIA study, disclosed verbatim
across their Facebook/X/Instagram/LinkedIn posts (the full blog article
URL 404s, but the mechanical rule is stated identically across all
social channels): "DIA just printed an outside day after an inside day,
triggering a simple mean-reversion setup... buy DIA at the next open
after this pattern appears. Since 1998: 125 trades, 76% win rate."
Related concept: their "HHLL Trading Strategy" article states "the HH and
LL constitute what is called an outside day."

## Hypothesis
An inside day immediately followed by an outside day (2-bar sequence: day
t-1 fully contained within day t-2's range, day t's range fully engulfs
day t-1's range) triggers a long entry at the next bar's open; exit after
a fixed holding period.

## Grid test (Step 6)
`param_grid={"hold_days": [3, 5, 7, 10]}`, symbols
`{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Total: 6/48 pass (12.5%)**
- By asset class: equity 6/24 (25%), crypto 0/24 (0%)
- By vol regime: low 3/16 (18.75%), mid 0/16 (0%), high 3/16 (18.75%) —
  notably the ONLY strategy tested in this repo so far that passes some
  high-vol cells while failing ALL mid-vol cells; an unusual, likely
  noisy bimodal pattern rather than a genuine regime-dependent edge.
- Best cell: `hold_days=7`, QQQ, high-vol, Sharpe 1.43
- Worst cell: `hold_days=3`, QQQ, mid-vol, Sharpe -1.12

## Single-config validation (Step 7), best grid config `hold_days=7`

| Symbol | Sharpe | Threshold | Pass | MDD | Threshold | Pass | TC net Sharpe | Threshold | Pass |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 0.764 | 1.0 | No | 0.160 | 0.25 | Yes | 0.704 | 0.5 | Yes |
| SPY | 0.354 | 1.0 | No | 0.109 | 0.25 | Yes | 0.258 | 0.5 | No |

## Decision: REJECTED

Full-sample Sharpe fails on both symbols (0.764 QQQ is a moderate
near-miss, 0.354 SPY is a decisive fail), and SPY additionally fails
transaction-cost-survival (35 trades erodes a thin edge). The grid's
apparent equity 25% pass rate is driven by an inconsistent, noisy
low-vol/high-vol split with zero mid-vol passes — not a clean, tradeable
regime pattern. Unlike the source's own DIA-specific claim (76% win rate,
125 trades since 1998), this repo's QQQ/SPY test since 2019 does not
reproduce a comparable edge; DIA itself was not tested (not in this
repo's standard symbol set) and may behave differently. Crypto rejected
decisively (0/24 grid cells).
