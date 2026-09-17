# Pairs Ratio Trend & Pullback (D'Errico, TASC Dec 2016) — Rejected

**Source:** https://traders.com/Documentation/FEEDbk_docs/2016/12/TradersTips.html
(Domenico D'Errico, "Pair Trading With A Twist", TASC Dec 2016; TradeStation
EasyLanguage "PairsStrategy" code disclosed, "Trend & Pullback" mode)

**Hypothesis:** Price-ratio (primary/hedge symbol) smoothed by fast (12) and
slow (40) SMAs. When fast SMA > slow SMA (uptrend in the ratio) AND the raw
ratio pulls back to cross under the fast SMA, buy the numerator symbol on
the pullback (trend-continuation entry, not a fresh breakout). Exit on the
ratio reclaiming the fast SMA or the trend state flipping. Tested QQQ/SPY
(equity pair) and ETH/BTC (crypto pair).

## Grid summary (72 cells total: equity 36 QQQ/SPY, crypto 36 ETH/BTC)

- overall pass_fraction: 0.2778 (20/72)
- equity (QQQ/SPY): pass_fraction 0.389 (14/36) — **low-vol regime 12/12
  (100%)**, mid 2/12, **high 0/12**
- crypto (ETH/BTC): pass_fraction 0.167 (6/36) — low 4/12, mid 2/12, high 0/12
- best config by avg-Sharpe: QQQ, fast_length=8, slow_length=40,
  max_hold_days=15/25 — 2/3 regimes passed, avg Sharpe 0.90

## Single-config validation (QQQ/SPY, fast_length=8, slow_length=40,
max_hold_days=15)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.839 | >= 1.0 | FAIL |
| Max drawdown | 11.2% | <= 25% | PASS |
| TC survival (net Sharpe, 125 trades) | 0.599 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 0.75 (3/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (relative std) | 0.505 | <= 0.5 | FAIL (barely) |

## Verdict: REJECTED

Full-sample Sharpe (0.839) misses the 1.0 threshold, and parameter
sensitivity (0.505) barely exceeds its 0.5 cap — two of five validators
fail. The strategy's edge is entirely a low-vol-regime phenomenon (100%
pass rate there vs 0% in high-vol for both asset pairs), and 125 trades on
QQQ over 7.5 years suggests fairly high turnover for a pullback-continuation
system, eating into the net-of-cost edge (TC-survival only just clears 0.5).
Not accepted; the trend-continuation "pairs ratio pullback" mechanic itself
does not appear to add value over this repo's existing single-asset trend
filters.
