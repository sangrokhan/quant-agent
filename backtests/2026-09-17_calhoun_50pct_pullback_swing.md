# Calhoun 50% Pullback Swing (Mean-Reversion Swing Trading, TASC Dec 2016/Jan 2017) — Rejected

**Source:** https://traders.com/Documentation/FEEDbk_docs/2017/01/TradersTips.html
(Ken Calhoun, "Mean-Reversion Swing Trading", TASC Dec 2016 article / Jan
2017 Traders Tips code; TradeStation EasyLanguage disclosed)

**Hypothesis:** A fresh 20-day channel extreme sets a "LongOK" state; the
50% retracement level between that high and the most recent opposing low
becomes a trigger line. When the setup state persists 2+ bars and price
closes back above the trigger line while above a 50-day SMA, enter long
(pullback-into-uptrend entry). Exit on the trigger line breaking back down
or the SMA trend filter failing.

## Grid summary (216 cells: 3 chan_length x 2 ma_length x 3 max_hold_days
x 4 symbols x 3 vol regimes)

- pass_fraction: 0.1065 (23/216) — weak overall
- by_asset_class: equity 14/108, crypto 9/108
- by_vol_regime: low 11/72, mid 9/72, high 3/72
- best config by avg-Sharpe: SPY, chan_length=15, ma_length=30,
  max_hold_days=15 — 2/3 regimes passed, avg Sharpe 1.30

## Single-config validation (SPY, chan_length=15, ma_length=30,
max_hold_days=15)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.068 | >= 1.0 | PASS |
| Max drawdown | 1.7% | <= 25% | PASS |
| TC survival (net Sharpe, **2 trades**) | 1.046 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 1.0 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (relative std) | 0.932 | <= 0.5 | FAIL (decisive) |

## Verdict: REJECTED (statistically degenerate)

Only **2 trades** occurred on SPY over the full 2019-2026 sample at this
config -- far too sparse to draw any statistical conclusion despite every
per-trade metric (Sharpe, MDD, TC-survival, walk-forward) technically
passing. The extreme parameter sensitivity (relative_std 0.93, nearly
double the 0.5 threshold) confirms this: neighboring parameter values in
the grid produce wildly different (often negative) Sharpe ratios, meaning
the apparent "pass" is a fragile artifact of this exact parameter
combination rather than a robust edge. The 50%-retracement 2-consecutive-
bar setup state is simply too restrictive to fire often enough on daily
bars to be a credible strategy.
