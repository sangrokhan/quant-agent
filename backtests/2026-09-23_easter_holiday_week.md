# 2026-09-23 — Easter Holiday Week Seasonal Effect

## Hypothesis

Per QuantifiedStrategies.com's "Easter Trading Strategy: Does the Stock
Market Rally Before the Holiday?"
(https://quantifiedstrategies.substack.com/p/easter-trading-strategy-does-the,
read via browser_exec this iteration — web_search DDGS/Yahoo backend
TLS-errored on every query attempted): buy at the close of the Friday
preceding Easter week, sell at the close of Holy Thursday (the trading day
immediately before the Good Friday market closure). Source's own S&P 500
backtest since 1960 claims avg gain/trade 0.7% (65yr) to 1.3% (since 2000),
MDD as low as 2%. Novel calendar-anomaly construction, no prior Easter/Good
Friday entry in this repo.

Source URL: https://quantifiedstrategies.substack.com/p/easter-trading-strategy-does-the

## Light-workload screening result (suggested_workload=light per gate)

Full-sample Sharpe/MDD, 2010-2026 (16 years, to get a larger trade count
than the default 2018-2026 window given the very low trade frequency of a
once-a-year calendar effect):

| symbol | Sharpe | MDD | # trades |
|---|---|---|---|
| SPY | 0.430 | 0.059 | 17 |
| QQQ | 0.385 | 0.094 | 17 |
| BTC/USDT | 0.074 | 0.136 | 9 |
| ETH/USDT | 0.091 | 0.212 | 9 |

All 4 symbols miss min_sharpe=1.0 decisively (0.07–0.43, well under
half the threshold). MDD is low for equities (as the source claims) but
the low absolute drawdown reflects the tiny holding-period exposure
(~1 week/year), not a strong risk-adjusted edge — the underlying gains are
real but too small/inconsistent (mixed positive/negative days within each
holiday window, see raw per-trade returns) to clear the Sharpe bar once
annualized against a near-fully-flat return series.

## Decision: REJECTED (no full grid/validator suite run — decisive
full-sample Sharpe miss across all 4 screening symbols/asset classes makes
further validation uninformative per RESEARCH_LOOP.md Step 7's
light-workload guidance)

Trade count is also structurally very low (~1 trade/year by construction,
a once-a-year calendar event) — even with a longer 16-year lookback, only
17 equity trades were available, making any Sharpe estimate here
noisy/low-power regardless of the point estimate. Recording as rejected
rather than a near-miss since the point estimates are far below threshold
on all 4 tested symbols, not close to the 1.0 bar.
