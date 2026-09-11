# 2026-09-11 Kiss of Death Bear-Market Signal — Backtest Report

**Hypothesis:** Monthly-bar 4-step sequential sell signal: (1) index makes
an all-time high, (2) closes a month below its 21-month EMA, (3) bounces
back above the 21-month EMA, (4) then closes a month below the low made
just before the bounce -- confirmed exit to flat; re-enter when the index
closes a month above its 10-month EMA. Source:
https://www.quantifiedstrategies.com/kiss-of-death-trading-strategy/
(visited this iteration, fully disclosed rule and backtest). Source's own
SPX backtest since 1967: CAGR 9.08% vs buy-and-hold 7.11%, time in market
87.9%, MDD 30.17% vs buy-and-hold 52.56%.

## Single-config validators (SPY 1993-2024, QQQ 1993-2024, default ema_fast=21/ema_slow=10)

| Symbol | Sharpe | MDD | Transaction cost (10bps, switch count) | Passed |
|---|---|---|---|---|
| SPY | 0.769 | 0.341 | net Sharpe 0.768 ✅ (only 6 switches) | Sharpe FAIL, MDD FAIL |
| QQQ | 0.520 | 0.830 | net Sharpe 0.520 ✅ (only 2 switches) | Sharpe FAIL, MDD FAIL |
| BTC/USDT | 0.112 | 0.814 | n/a | FAIL |
| ETH/USDT | 0.137 | 0.943 | n/a | FAIL |

## Decision: REJECTED (decisively, all symbols)

Unlike this cron trigger's other two rejections (2026-09-11-072,
2026-09-11-074, both near-miss on transaction costs only), this strategy
clears transaction-cost survival easily (it trades only 2-6 times over
30 years, since the signal is designed to fire extremely rarely) but
fails Sharpe AND max drawdown decisively on every symbol tested. QQQ's
83% max drawdown confirms the strategy stayed long through the entire
2000-2002 dot-com crash (QQQ inception 1999, so its only "kiss of death"
opportunity would need a fresh all-time-high before the crash, which
didn't cleanly materialize under this repo's monthly-close-based
reconstruction) and other severe drawdowns. Crypto is decisively
inapplicable -- BTC/ETH's parabolic-boom-then-70-90%-drawdown cycles are
structurally different from equity index bear markets and the 21/10-month
EMA thresholds calibrated for SPX give no useful signal (0.814/0.943 MDD,
essentially unhedged buy-and-hold with worse Sharpe).

This is a case where the source's own qualitative framing ("triggered
rarely, historically accurate, but false signals possible... 2022 signal
did not result in a huge drop") undersold the risk that this repo's
strict monthly-close reconstruction did not fully replicate the
source's original signal timing/context (their own backtest starts in
1967 with different index-history nuances) -- the source's own headline
MDD improvement (30.17% vs 52.56% buy-and-hold) was NOT reproduced here;
this repo's SPY MDD (34.1%) is actually WORSE than a naive full test would
suggest is "improved" over buy-and-hold, and QQQ dramatically fails.

## Notes for future iterations

- First monthly-bar, multi-step sequential state-machine pattern in this
  repo (all-time-high -> EMA break -> failed bounce -> lower-low
  confirmation) -- structurally distinct from every single-condition
  signal already tested, worth remembering as "state-machine construction
  works technically (implemented, ran, produced signals) but this
  specific EMA-based bear-signal rule doesn't reproduce the source's own
  claimed MDD-avoidance benefit in this repo's SPY/QQQi backtest window."
- A future iteration attempting a similar sequential-pattern construction
  should validate the SIGNAL TIMING carefully against the source's own
  worked example (Sept 2008 trigger) before trusting the general
  mechanic, since this repo's implementation may have subtly mis-timed
  the state transitions (e.g. the source's "10-month EMA" re-entry
  criterion, chosen by the source purely because "it performed generally
  well" with no principled derivation, may need its own independent
  re-tuning rather than taking the source's number at face value).
