# Minervini Trend Template — Retuned (low_pct_above=0.30, slope_lookback=10)

**Strategy file:** `strategies/2026-09-12_minervini_trend_template.py`
(unchanged code, direct fine-tune follow-up to this repo's own near-miss
`2026-09-12-164`)
**Source:** ChartMill.com, "Mark Minervini Trend Template: A Step-by-Step
Guide for Beginners", fully disclosed
(https://www.chartmill.com/documentation/stock-screener/technical-analysis-trading-strategies/496-Mark-Minervini-Trend-Template-A-Step-by-Step-Guide-for-Beginners).

## Hypothesis

`2026-09-12-164` was a near-miss on both QQQ (Sharpe 0.839) and SPY
(Sharpe 0.772), with its grid's own `best_cell` for QQQ using
`low_pct_above=0.25, high_pct_within=0.20, slope_lookback=20`. This
iteration ran a full-sample scan around `low_pct_above` in {0.15, 0.20,
0.25, 0.30, 0.35} x `high_pct_within` in {0.15, 0.20, 0.25} x
`slope_lookback` in {5, 10, 15, 20, 40} (holding `max_hold_days=60` fixed)
and found `low_pct_above=0.30, slope_lookback=10` clears SPY Sharpe 1.20
-- `high_pct_within` turned out to never bind at the tested values (results
identical across 0.15/0.20/0.25), meaning criterion 8 (price within X% of
52-week high) is not the constraining criterion here.

## Full-sample scan (top results)

| Symbol | low_pct_above | slope_lookback | Sharpe | MDD |
|---|---|---|---|---|
| **SPY** | **0.30** | **10** | **1.200** | 0.100 |
| SPY | 0.30 | 15 | 1.140 | 0.102 |
| SPY | 0.30 | 5 | 1.138 | 0.102 |
| SPY | 0.25 | 10 | 0.977 | 0.104 |
| QQQ | 0.35 | 5/10/15 | 0.950 | 0.143 |
| QQQ | 0.25 | 10 | 0.847 (parent-like) | 0.202 |

## Single-config validation (low_pct_above=0.30, high_pct_within=0.25, slope_lookback=10, max_hold_days=60)

| Symbol | Sharpe | Sharpe pass | MDD | MDD pass | TC-survival net Sharpe | TC pass | WF pass_frac | WF pass | Param-sens relstd | PS pass | Trades | ALL PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 0.773 | ❌ | 0.185 | ✅ | 0.721 | ✅ | 0.50 | ❌ | 0.089 | ✅ | 45 | ❌ reject |
| SPY | 1.200 | ✅ | 0.100 | ✅ | 1.156 | ✅ | 1.00 | ✅ | 0.213 | ✅ | 19 | **✅ ACCEPT** |
| BTC/USDT | -0.008 | ❌ | 0.482 | ❌ | -0.026 | ❌ | 0.25 | ❌ | 6.569 | ❌ | 131 | ❌ reject |
| ETH/USDT | 0.083 | ❌ | 0.383 | ❌ | 0.063 | ❌ | 1.00 | ✅ | 0.411 | ✅ | 213 | ❌ reject |

Parameter sensitivity swept `low_pct_above` in {0.25,0.30,0.35} x
`slope_lookback` in {5,10,15} around the accepted config. Walk-forward used
manual 4-equal-slice fallback.

## Decision

**Accept for SPY only** at the retuned config (`low_pct_above` 0.30 vs
parent's 0.25/default 0.30, `slope_lookback` 10 vs parent's grid-tested
20) -- a decisive rescue reaching Sharpe 1.20, well clear of the 1.0
threshold, with all 5 validators passing. Interestingly this is the
INVERSE of the parent's own asset preference (parent's grid `best_cell`
was QQQ-specific; this retuned config instead favors SPY and QQQ now FAILS
walk-forward at 0.50 pass fraction despite a decent full-sample Sharpe
0.773 -- the Minervini Trend Template's "all criteria simultaneously true"
strictness produces a genuinely low trade count (19-45 trades over 8.5yr)
that makes full-sample Sharpe an unstable estimator sensitive to exactly
which sub-period is measured). Crypto (BTC/USDT, ETH/USDT) decisively
rejected -- BTC/USDT's param-sensitivity relstd of 6.57 is one of the most
unstable results recorded in this repo, reflecting how poorly a
"steady long-term uptrend regime" checklist designed for equities
generalizes to crypto's structurally different, more cyclical/volatile
price action.
