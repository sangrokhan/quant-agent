# January Effect Small-Cap Seasonal Long (IWM)

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_january_effect_smallcap_seasonal.py`
**KB id:** 2026-09-06-133

## Hypothesis

Per QuantPedia's "January Effect in Stocks" (citing Keim 1983,
tax-loss-selling hypothesis): small-cap stocks have historically shown
outsized January returns. QuantPedia's own page notes the effect has
weakened in recent decades ("transaction costs make it impossible to
trade this anomaly" recently) — this strategy tests that decay claim
directly: long IWM (and QQQ/SPY/crypto as comparators) only during
January's first N trading days each year, flat otherwise. First
January-Effect / small-cap seasonal strategy in this repo, distinct from
already-tested Santa Claus Rally (~7-day year-end window) and Halloween
Effect (6-month hold).

**Source:** https://quantpedia.com/strategies/january-effect-in-stocks/
(browser_exec — historical background, decay/transaction-cost caveat,
1947-2007 backtest stats).

## Grid test (end_trading_day=[5,10,21], IWM/QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 7/45 cells passed (equity 7/27, **crypto 0/18 decisively rejected**
  — no January-effect analogue for crypto by construction)
- By vol regime: low 5/15, mid 0/15, high 2/15 — mostly a low-vol-slice
  effect
- Best cell: end_trading_day=10, IWM low-vol, Sharpe 2.206 (single tercile
  slice — a handful of trading days per year)

## Single-config validators (IWM, full sample 2019-2026)

| end_trading_day | Full-sample Sharpe | Trades |
|---|---|---|
| 5 | 0.580 | 40 |
| 10 | 0.770 | 80 |
| 21 | 0.626 | 161 |

| Validator (end_trading_day=10) | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL | 0.770 | ≥ 1.0 |
| Max drawdown | PASS | 9.2% | ≤ 25% |

## Decision: **REJECT**

Full-sample Sharpe fails for all three variants on IWM (the intended
small-cap proxy) despite an eye-catching low-vol-tercile Sharpe of 2.2 —
that single grid cell reflects only a handful of January trading days per
year in one vol regime, not a robust full-sample edge. This corroborates
QuantPedia's own caveat that the January effect has decayed to the point
of being untradeable after costs in the modern era. Skipped walk-forward/
TC-survival/parameter-sensitivity given the clear full-sample Sharpe miss
across all tested variants.
