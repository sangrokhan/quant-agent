# Three Outside Up (3-Candle Bullish Reversal) — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_three_outside_up.py`
**Source:** https://www.investopedia.com/terms/t/three-outside-updown.asp

## Hypothesis

Three Outside Up is a 3-candle bullish reversal distinct from this repo's
already-tested 2-candle Bullish Engulfing (2026-09-04-102, rejected;
volume-gated variant 2026-09-08-024, also rejected): downtrend context,
candle 1 bearish, candle 2 bullish fully engulfing candle 1's body
(standard bullish engulfing), and candle 3 bullish with a close HIGHER than
candle 2's close (an explicit confirmation/acceleration requirement plain
engulfing strategies don't have).

## Grid test (Step 6)

`param_grid={"trend_window": [30,50,100], "max_hold_days": [10,15]}`,
symbols QQQ/SPY/BTC-USDT/ETH-USDT, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01.

- **72 total cells, 0 passed (pass_fraction 0.0)** -- decisive rejection.
- Best cell Sharpe only 0.59 (SPY, high-vol), still below threshold.

## Single-config validators (trend_window=50, max_hold_days=15)

| Symbol | Trades | Sharpe (full) | MDD | TC-survival (net Sharpe) |
|---|---|---|---|---|
| QQQ | 10 | -0.178 **FAIL** | 0.160 PASS | -0.202 **FAIL** |
| SPY | 6 | 0.164 **FAIL** | 0.092 PASS | 0.141 **FAIL** |

## Decision: REJECTED

Decisive 0/72 grid cells across every asset class and vol regime. QQQ's
Sharpe is actually negative (-0.178) with negative net-of-cost returns.
Adding the third confirmation candle (vs. plain 2-candle Bullish Engulfing)
did not produce a rescuing edge -- if anything, the extra confirmation bar
means entries come one day later (after some of the reversal move has
already happened), which may explain the weaker results relative to even
the plain engulfing predecessor's near-misses elsewhere in this repo.
Crypto also failed all cells. This closes out the engulfing-pattern family
(plain engulfing, volume-gated engulfing, three outside up -- 3 variants)
for this repo's scope.
