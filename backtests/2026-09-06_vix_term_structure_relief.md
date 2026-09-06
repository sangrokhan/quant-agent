# VIX Term-Structure "Buy the Relief" (Backwardation Resolution)

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_vix_term_structure_relief.py`
**KB id:** 2026-09-06-127

## Hypothesis

Per Options Cafe's 17-year VIX/VIX3M term-structure study: buying at the
*onset* of VIX backwardation (VIX > VIX3M) has no edge (coin-flip at 5
days), but buying at *resolution* (ratio crosses back below 1.0 after being
in backwardation) was positive 88-91% of the time at +5/+21/+63 trading
days. Operationalized on SPY/QQQ: 5/10-day smoothed VIX/VIX3M ratio, long
entry on the resolution crossing, fixed hold (21/42/63 days) or immediate
exit on fresh onset.

**Source:** https://options.cafe/blog/vix-term-structure-contango-backwardation/
(browser_exec; web_search errored on this iteration's query).

First VIX-term-structure strategy in this repo — a genuinely different
signal class (relative implied-vol term-structure pricing, not price/volume
technicals).

## Grid test (smooth_window=[3,5,10] x hold_days=[21,42,63], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 31/108 cells passed (equity 31/54, **crypto 0/54** — expected/by-construction, since VIX/VIX3M is an S&P 500-options signal with no crypto analogue implemented, strategy stays flat on crypto)
- By vol regime: low 15/36, mid 2/36, **high 14/36** — notably works in BOTH low and high vol regimes, fails mid-vol (a genuinely different regime pattern vs. most prior accepted strategies in this repo, which typically only work in low-vol)
- Best avg-config: smooth_window=10, hold_days=63, QQQ avg Sharpe 1.30 across regimes

## Single-config validators (QQQ, smooth_window=10, hold_days=63, full sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL (near-miss)** | 0.902 | ≥ 1.0 |
| Max drawdown | PASS | 22.6% | ≤ 25% |
| TC survival (10bps, 8 trades) | PASS | net Sharpe 0.890 | ≥ 0.5 |
| Walk-forward (manual 4-split) | PASS (borderline) | 3/4 = 0.75 | ≥ 0.75 |
| Parameter sensitivity (9-cell QQQ sweep) | PASS | relative_std 0.152 | ≤ 0.5 |

SPY sanity check at same config: Sharpe 0.802 (positive, consistent
direction, lower magnitude).

## Decision: **REJECT (near-miss)**

Full-sample Sharpe (0.902) misses the 1.0 threshold on the primary QQQ
config despite every other validator passing and unusually low parameter
sensitivity (0.152, one of the most stable grids tested in this repo). This
is a genuine near-miss worth flagging for a future iteration to revisit —
e.g. tighter entry filter (require a minimum backwardation depth/duration
before counting as a valid episode, per the source's own note that
"episodes merge spikes separated by fewer than five days") or testing on
raw index returns (^GSPC) instead of the ETF wrapper. Only 8 trades over
7.7 years also means this is a fairly sparse signal — the Sharpe estimate
carries real uncertainty.
