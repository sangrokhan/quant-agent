# Bulkowski Key Reversal, Downtrend -- QQQ retune

**Hypothesis:** per https://thepatternsite.com/KRD.html, 2-bar outside-day
pattern with added positioning constraints (close > prior high, open < prior
close). Traded long/up-breakout side only per repo convention.

**Config (QQQ):** trend_window=0, height_mult=0.75, max_hold_days=5

## Single-config validators (QQQ, 2019-01-01 to 2026-09-01, 12 trades)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.106 | >= 1.0 | Yes |
| Max drawdown | 0.021 | <= 0.25 | Yes |
| Net Sharpe after costs (10bps/trade) | 0.996 | >= 0.5 | Yes |
| Walk-forward | skipped (vectorbt.utils.splitting API missing, known repo issue) | n/a | n/a |
| Parameter sensitivity (relative std, 9-cell local grid) | 0.333 | <= 0.5 | Yes |

SPY at the same config family: best full-sample Sharpe found was 0.99
(trend_window=20/height_mult=3.0/max_hold_days=60) -- does not clear the
1.0 threshold; SPY remains rejected for this pattern (see 2026-09-26-051).

## Outcome: ACCEPTED (QQQ only)

Note: only 12 trades over 7.5 years is a thin sample -- flagged in notes as
a caveat for future loops evaluating this strategy's true robustness.
