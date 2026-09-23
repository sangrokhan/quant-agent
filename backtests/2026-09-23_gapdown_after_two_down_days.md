# 2026-09-23 — Unfilled Gap-Down After Two Down Days (3-Day Capitulation Pattern)

## Hypothesis

Per QuantifiedStrategies.com's "Unfilled Gap Trading Strategies"
(https://www.quantifiedstrategies.com/unfilled-gap-trading-strategies/,
read via browser_exec this iteration — web_search DDGS/Yahoo backend
TLS-errored on every query attempted): two consecutive close-to-close down
days followed by an unfilled gap-down (today's high < yesterday's low) on
the third day — a 3-day capitulation-exhaustion pattern. Enter long at the
close of the gap day; exit after a fixed hold_days holding period.
Structurally distinct from the already-tested/rejected single-RSI-filter
variant (2026-09-11-084).

Source URL: https://www.quantifiedstrategies.com/unfilled-gap-trading-strategies/

## Light-workload screening result (suggested_workload=light per gate)

Full-sample Sharpe/MDD, 2010-2026:

| symbol | hold_days | Sharpe | MDD | # trades |
|---|---|---|---|---|
| SPY | 3 | 0.643 | 0.140 | 44 |
| SPY | 5 | 0.465 | 0.168 | 44 |
| SPY | 10 | 0.398 | 0.227 | 42 |
| QQQ | 3 | 0.115 | 0.265 | 46 |
| QQQ | 5 | 0.452 | 0.195 | 46 |
| QQQ | 10 | 0.624 | 0.219 | 44 |

All 6 cells miss min_sharpe=1.0 decisively (max 0.643), with no cell close
to passing.

## Decision: REJECTED (no full grid/validator suite run — decisive
full-sample Sharpe miss across all 6 screening cells makes further
validation uninformative per RESEARCH_LOOP.md Step 7's light-workload
guidance)

Confirms the source's own conclusion that unfilled gap patterns "are not
tradeable on their own" even with the more selective 3-day capitulation
AND-gate — same qualitative finding as the previously-rejected simpler
RSI-filtered variant (2026-09-11-084), now confirmed for this structurally
distinct construction too.
