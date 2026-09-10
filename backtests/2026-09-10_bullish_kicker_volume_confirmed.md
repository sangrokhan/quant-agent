# 2026-09-10 — Bullish Kicker Candlestick Pattern, Volume-Spike Confirmed (REJECTED)

## Hypothesis

Per https://www.quantifiedstrategies.com/bullish-kicker-candlestick-pattern/:
the Bullish Kicker pattern is (1) a bearish candle, followed by (2) a candle
that gaps UP — opens above the prior day's close — and closes as a bullish
candle with the gap left completely unfilled (day2's low stays above day1's
close). Source qualitatively suggests volume confirmation strengthens the
signal (not numerically backtested by the source). This implementation adds
a numeric volume-spike filter (volume >= vol_mult x trailing average) as the
testable operationalization of that suggestion.

Strategy file: `strategies/2026-09-10_bullish_kicker_volume_confirmed.py`

## Grid summary (vol_mult in [1.2,1.5,2.0] x max_hold_days in [10,15,20], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- 0/108 cells passed (pass_fraction 0.0) — decisive rejection across every
  symbol/vol-regime/param combination.
- Best cell: QQQ, vol_mult=1.2, max_hold_days=10, low-vol tercile, Sharpe
  0.82 (still below the 1.0 threshold).
- Worst cell: QQQ, vol_mult=1.2, max_hold_days=10, mid-vol tercile, Sharpe -0.72.

## Decision: REJECT

Decisive rejection. The pattern is structurally very rare (only 24 signals
fired for SPY over the ~10-year sample at the default vol_mult=1.5), and
even the best grid cell's Sharpe (0.82) falls short of the 1.0 threshold.
This is consistent with the pattern's own literature framing as a strong
but infrequent signal — insufficient sample size and no config reaches the
Sharpe bar in this repo's grid. Full validator suite skipped as unnecessary
given the decisive 0/108 grid result.
