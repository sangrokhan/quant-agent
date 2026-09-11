# 2026-09-11 Post-Midterm-Election 12-Month Rally — Backtest Report

**Hypothesis:** Long the primary asset for 12 months starting November 1st
of a U.S. midterm-election year (year % 4 == 2: 1994, 1998, ..., 2018,
2022), flat otherwise. Source:
https://www.quantifiedstrategies.com/sp500-midterm-election-year/
(visited this iteration, fully disclosed calendar rule + cited historical
stats). Source cites U.S. Bank/E*TRADE data: S&P 500 averaged 16.3% in
the 12 months after midterms across 15 cycles studied, with no negative
12-month return since 1939.

## Single-config validators (SPY/QQQ 1993-2024, start_month=11, hold_months=12)

| Symbol | Sharpe | MDD | Switches | Net Sharpe (10bps) |
|---|---|---|---|---|
| SPY | 0.496 (fail) | 0.201 ✅ | 16 | 0.489 |
| QQQ | 0.626 (fail) | 0.183 ✅ | 12 | 0.620 ✅ |
| BTC/USDT | 0.122 (fail) | 0.519 (fail) | -- | -- |
| ETH/USDT | 0.048 (fail) | 0.650 (fail) | -- | -- |

## Decision: REJECTED (decisive on Sharpe, all 4 symbols)

Both SPY and QQQ fail Sharpe decisively despite passing MDD and (for
QQQ) transaction-cost survival -- this repo's longer, more recent
1993-2024 sample (spanning 8 midterm cycles: 1994, 1998, 2002, 2006,
2010, 2014, 2018, 2022) does not reproduce the source's cited 16.3%-
average/never-negative claim strongly enough to clear a 1.0 Sharpe
threshold, even though the underlying directional bias (spending ~26%
of calendar time in a positive-tilted window) is not unreasonable (both
symbols pass MDD easily and QQQ even clears transaction costs). This
reads as a case of a real but MODEST calendar tilt that is not strong
enough on its own to constitute an accepted standalone trading strategy
by this repo's Sharpe bar -- similar in character to several other
calendar-effect near-misses/rejections already logged (Turn-of-Month,
Sell-in-May, January Effect family). Crypto is decisively inapplicable
(no US-election-cycle analog reason to expect an effect, and results
confirm no edge: 0.05-0.12 Sharpe, 52-65% MDD).

## Notes for future iterations

- Distinct from the already-tested 4-year PRESIDENTIAL-election-cycle
  strategy (2026-09-08-163, years 3-4 vs years 1-2 of a full term) --
  this is a narrower, specifically MIDTERM-anchored 12-month window
  (Nov of the midterm year through Oct of the following year) rather
  than a full-term-year classification; both now confirmed insufficient
  to clear this repo's Sharpe bar on their own.
- A future iteration could try COMBINING this midterm-year tilt with an
  existing accepted trend/momentum filter (only take the seasonal long
  when an independent trend confirmation is also present) rather than
  trading the calendar window unconditionally -- several other
  successfully-accepted seasonal strategies in this repo (e.g.
  2026-09-05-072 Turn-of-Month + weakness precondition) used exactly
  this "calendar window AND confirming filter" combination pattern to
  clear thresholds that the calendar effect alone could not.
