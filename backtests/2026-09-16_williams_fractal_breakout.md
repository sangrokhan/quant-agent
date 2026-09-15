# Backtest report: Williams Fractal Breakout (2026-09-16)

**Strategy file:** `strategies/2026-09-16_williams_fractal_breakout.py`
**KB entry:** `2026-09-16-186` (rejected)

## Hypothesis

Per Bill Williams' Fractal indicator (Google search snippet synthesis +
LiteFinance/Quantified Strategies/TradingView), a Fractal high/low is a
5-bar pattern with a strict local extreme at the center (2-bar confirmation
lag). Per LiteFinance's own breakout rule: a decisive close above the most
recently confirmed Fractal high triggers a long entry, stop below the most
recently confirmed Fractal low, exit at stop or a `max_hold_days`
time-stop.

First Williams Fractal strategy in this knowledge base.

**Source:** Google SERP snippet text (direct LiteFinance article URL
404'd on fetch — rules were specific/numeric enough in the visible search
snippet to implement without the full article).

## Grid test (Step 6)

`GridSpec(param_grid={"max_hold_days": [5,10,15,20,30]}, symbols={"equity":
["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}, vol_regime_splits=3)` —
60 cells, 2018-01-01 to 2026-09-01.

| metric | value |
|---|---|
| pass_fraction | 14/60 = 0.233 |
| by_asset_class | equity 11/30, crypto 3/30 |
| by_vol_regime | **low 13/20, mid 1/20, high 0/20** |
| best cell | QQQ, max_hold_days=30, low-vol, Sharpe 2.376 |

## Single-config validators (full-sample)

| symbol | max_hold_days | sharpe | mdd |
|---|---|---|---|
| QQQ | 15 | 0.505 ❌ | 0.294 ❌ |
| QQQ | 20 | 0.623 ❌ | 0.360 ❌ |
| QQQ | 30 | 0.650 ❌ | 0.419 ❌ |
| SPY | 15 | 0.515 ❌ | 0.250 ✅ |
| SPY | 20 | 0.545 ❌ | 0.232 ✅ |
| SPY | 30 | 0.544 ❌ | 0.346 ❌ |

No config clears the Sharpe threshold full-sample for any symbol. The
grid's 23% pass fraction is entirely a low-vol-regime artifact (13/20 of
all passes), not corroborated by the full-sample numbers.

## Decision

**Rejected.** Full-sample Sharpe fails decisively for every tested
max_hold_days value on both QQQ and SPY. The grid's apparent pass rate is
concentrated almost entirely in the low-vol-regime tercile, consistent
with the recurring overfitting pattern seen in several other rejected
strategies this cron trigger (Market Profile Value Area re-entry,
Bullish Engulfing) — a narrow favorable sub-period, not a genuine broad
edge.
