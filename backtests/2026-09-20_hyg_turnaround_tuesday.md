# Backtest Report: HYG (Junk Bond ETF) Turnaround Tuesday Day-of-Week Seasonality

**Strategy file:** `strategies/2026-09-20_hyg_turnaround_tuesday.py`
**Date:** 2026-09-20
**Outcome:** REJECTED (near-miss, unconditional variant)

## Hypothesis

Per quantifiedstrategies.com's "Junk Bond Trading Strategies: Seasonality,
Backtest, Performance"
(https://www.quantifiedstrategies.com/junk-bond-trading-strategies/, read
via browser_exec fallback -- web_search DDGS backend hit repeated
TLS/connection-reset errors this iteration), a day-of-week backtest on HYG
found: "Monday is the weakest day while Tuesday is the best... hint that
there is a Turnaround Tuesday effect in junk bonds." This repo has tested
Turnaround Tuesday extensively on equities/crypto (7+ prior entries) but
never specifically on a junk-bond/credit-market ETF -- a genuinely new
asset class for this well-worn technique family. The source itself notes
junk bonds trend more and mean-revert less than equities, making the
day-of-week effect's transferability to this asset an open empirical
question.

Tested both the unconditional version (matching the source's disclosed
backtest exactly: long HYG Monday close -> Tuesday close) and this repo's
already-accepted Monday-down-conditional refinement (2026-09-20-002,
originally for SPY) applied to HYG.

## Full-sample results (HYG, 2010-01-01 to 2026-09-01, full available history)

| Variant | Sharpe | Max Drawdown | Nonzero-return days |
|---|---|---|---|
| Unconditional (source's exact rule) | 0.761 | 0.085 | 1545 |
| Monday-down-conditional | 0.575 | 0.099 | 798 |

Both fail the Sharpe >= 1.0 threshold. The unconditional version is a
genuine near-miss (0.76) with an unusually low max drawdown (0.085) --
HYG's lower volatility as a bond-like instrument compresses both the
gains and losses of this 1-day-hold strategy relative to equities. The
Monday-down conditional gate (which improved SPY's Sharpe in
2026-09-20-002) makes HYG's result WORSE here, not better -- consistent
with the source's own observation that junk bonds trend more than
equities (a "weakness begets more weakness" conditional gate designed for
mean-reverting equities may not transfer to a trendier asset).

## Decision

**REJECTED.** Neither variant clears the Sharpe threshold. The
unconditional near-miss (0.76, very low MDD) is flagged as a potential
future direction -- e.g. widening to a 2-day hold (Monday->Wednesday) or
testing on JNK (the other major junk-bond ETF) to see if the effect is
HYG-idiosyncratic or genuinely present in the junk-bond asset class -- but
this repo's Turnaround-Tuesday-family exploration is already extensive
(7+ entries across equity/crypto, now +1 for junk bonds), so a future loop
should weigh this against the family's overall saturation before
investing further iterations in it.
