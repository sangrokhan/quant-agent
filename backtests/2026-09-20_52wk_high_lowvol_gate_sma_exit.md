# Backtest Report: 52-Week High Breakout, Low-Vol-Regime-Gated, 200-SMA Exit

**Strategy file:** `strategies/2026-09-20_52wk_high_lowvol_gate_sma_exit.py`
**Date:** 2026-09-20
**Outcome:** REJECTED (rescue attempt failed -- worse than ungated parent)

## Hypothesis / rescue attempt

Direct follow-up to prior id 2026-09-20-054 (52-Week High breakout + 200d
SMA exit, near-miss REJECTED: SPY Sharpe 0.879, QQQ Sharpe 0.880). That
entry's grid-test notes flagged the effect as strongly concentrated in
low-vol regimes (pass_fraction by vol-regime: low 23/36, mid 3/36,
high 3/36) and suggested an explicit low-vol regime gate as the rescue
direction. This iteration adds that gate: entry requires low-vol regime
(20d realized vol <= trailing 252d median), and an early exit if the
regime flips to high-vol.

## Full-sample parameter search (SPY + QQQ jointly, 42 combos)

Same 42-combo `lookback_days` x `exit_sma_window` search as the parent
entry. Best shared config: `lookback_days=189, exit_sma_window=75`:

| Symbol | Sharpe | Max Drawdown |
|---|---|---|
| SPY | 0.560 | 0.111 |
| QQQ | 0.567 | 0.121 |
| BTC/USDT | 0.017 | 0.405 (fails MDD) |
| ETH/USDT | 0.030 | 0.399 (fails MDD) |

## Result: the rescue made it WORSE, not better

Best combined Sharpe with the low-vol gate is 0.56 (SPY/QQQ), materially
*lower* than the ungated parent's 0.88. The gate reduces max drawdown
further (0.11-0.12 vs 0.16-0.19 ungated) but at the cost of filtering out
too many of the strategy's best-performing entries -- likely because a
"new 52-week high" breakout inherently tends to occur in *rising*-vol
conditions immediately after the breakout (fresh momentum/volume), so
gating the entry itself on low-vol conflicts with the pattern's own
mechanics, unlike the BB-mean-reversion construction this gate pattern was
borrowed from (where mean-reversion genuinely works better ex-ante in
calm markets). The grid-test's earlier observation that MOST PASSING
CELLS happened to fall in low-vol *terciles* was a description of when the
strategy's outcome landed well after the fact, not a causal signal usable
as an ex-ante entry filter -- conflating those two is the likely reason
this "fix" backfired.

## Decision

**REJECTED.** This sub-iteration is a negative/documented result: the
low-vol regime gate is NOT a valid rescue for the 52-week-high near-miss
(2026-09-20-054) and should not be attempted again in this exact form. A
future loop revisiting this idea should instead try the source's Exit 2
(25% trailing stop) / Exit 3 (100-bar lowest close) alternatives, or test
on individual high-momentum stocks rather than index ETFs, per the parent
entry's other suggested directions.
