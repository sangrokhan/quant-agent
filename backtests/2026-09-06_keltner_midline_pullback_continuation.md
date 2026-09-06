# Keltner Channel Middle-Line Pullback (Trend Continuation)

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_keltner_midline_pullback_continuation.py`
**KB id:** 2026-09-06-136

## Hypothesis

Per ThinkMarkets' Keltner Channel guide: "Common ATR Keltner trading
strategies include the trend pullback (buying dips to the middle line in
an uptrend)." Third distinct Keltner Channel interpretation tested in
this repo (after upper-band breakout, accepted QQQ-only 2026-09-03-016;
and lower-band mean-reversion bounce, rejected 2026-09-05-074): entry on
a bounce off the EMA middle line while the broader trend (close >
SMA(trend_window)) remains up.

**Source:** https://www.thinkmarkets.com Keltner Channel indicator guide
(via Google SERP snippet, browser_exec) — "trend pullback (buying dips to
the middle line in an uptrend)" rule.

## Grid test (kc_window=[15,20,30] x trend_window=[50,100,200] x max_hold_days=[10,15], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 37/216 cells passed (equity 37/108, **crypto 0/108 decisively rejected**)
- By vol regime: low 23/72, mid 10/72, high 4/72 — mostly a low-vol effect
- Best cell: kc_window=20, trend_window=200, max_hold_days=10, SPY
  low-vol, Sharpe 2.801

## Single-config validators (SPY, kc_window=20, trend_window=200, max_hold_days=10, full sample 2019-2026)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL (near-miss) | 0.965 | ≥ 1.0 |
| Max drawdown | PASS | 13.4% | ≤ 25% |
| TC survival (10bps, 442 trades) | **FAIL (decisive)** | net Sharpe -0.089 | ≥ 0.5 |

QQQ full-sample Sharpe: 0.895 (also below threshold). Parameter
sensitivity across a 9-cell SPY sweep: relative_std 0.309 (PASS, ≤0.5) —
the strategy is not wildly overfit to one parameter combo, but it's
structurally too high-frequency: 442 trades over 7.7 years (short
`max_hold_days` combined with a mean-reverting-to-midline exit) means
transaction costs completely erase the edge.

## Decision: **REJECT**

Despite a near-miss raw Sharpe (0.965 on SPY) and reasonable parameter
stability, the strategy fails transaction-cost survival decisively (net
Sharpe goes negative at just 10bps/trade due to high trade frequency).
This is a structural problem (frequent midline touches trigger too many
short-lived trades), not a parameter-tuning issue — the underlying
"buy dips to the middle line" idea would need either a much longer hold
period or a stricter re-entry cooldown to be economically tradeable.
