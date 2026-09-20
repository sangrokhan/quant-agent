# NR7 (Narrow Range 7) Breakout with Trend-SMA Filter (QQQ)

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_nr7_breakout_trend_filter.py`
**Source:** Toby Crabel's NR7 concept, corroborated across Google SERP
this iteration (browser_exec fallback — web_search DDGS backend
TLS-connection-errored on every query): [Quantified Strategies NR7 Trading
Strategy](https://www.quantifiedstrategies.com/nr7-trading-strategy/),
[ForexTrainingGroup — Simple Tactics For Trading Narrow Range
Bars](https://forextraininggroup.com/simple-tactics-for-trading-narrow-range-bars-nr4-nr7/)
(disclosed the 89-SMA directional filter used here), Scribd's "NR7 Forex
Trading Strategy Guide" (disclosed buy-stop-above-NR7-high entry rule).

## Hypothesis

The NR7 bar (narrowest high-low range of the trailing 7 bars) signals a
volatility contraction that historically precedes a volatility-expansion
breakout (Crabel's original thesis, also cited by Linda Raschke/Larry
Connors). Long entry: price breaks above the NR7 bar's high (small buffer)
while above its long-term trend SMA (89-period, per ForexTrainingGroup's
disclosed filter — tested here alongside 50/150 as a robustness check);
exit after a `max_hold_days` time-stop (no disclosed exit rule beyond
entry in any source).

## Grid test summary (`grid_result_nr7_breakout_trend_filter.json`)

- Grid: `trend_sma` ∈ {50, 89, 150} × `max_hold_days` ∈ {5, 10} × symbols
  {QQQ, SPY, BTC/USDT, ETH/USDT} × 3 vol terciles = 72 cells.
- **pass_fraction: 0.306** (22/72)
- By asset class: equity 19/36, crypto 3/36 — largely equity-only edge.
- By vol regime: low 15/24, mid 7/24, **high 0/24** — fails in high-vol
  regimes across the board.
- Best cell: SPY, trend_sma=150/max_hold_days=5, low-vol, Sharpe=2.40.

## Single-config validation (QQQ, trend_sma=50, max_hold_days=10, full sample 2017-2026)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.036 | ≥1.0 |
| Max drawdown | ✅ | 0.195 | ≤0.25 |
| Transaction cost survival (10bps/trade, 179 trades) | ✅ | 0.809 net Sharpe | ≥0.5 |
| Walk-forward (4-split manual) | ✅ | 1.0 (4/4 positive) | ≥0.75 |
| Parameter sensitivity (trend_sma×max_hold_days sweep) | ✅ | 0.156 relative std | ≤0.5 |

All 5 validators pass on QQQ full-sample. **Accepted, equity-only, and only
robustly full-sample-tested on QQQ** (SPY's best full-sample config,
trend_sma=89/max_hold_days=5, only reached Sharpe=0.871 — below the 1.0
bar; SPY did NOT independently pass full-sample at any tested combo).

## Notes

- Crypto (BTC/USDT, ETH/USDT) largely failed (3/36); high-vol regime fails
  universally across all symbols/params — consistent with a
  mean-reversion-of-volatility thesis not holding once volatility is
  already elevated.
- 179 trades over ~9.7 years (roughly 18/year) — moderate turnover for a
  10-day max-hold breakout strategy; transaction-cost survival still holds
  comfortably at 10bps/trade.
- First NR7/narrow-range-bar strategy in this repo — distinct from
  Donchian/52-week-high/ATR-channel breakouts (which key off a rolling
  EXTREME price level, not a rolling-minimum-RANGE bar).
