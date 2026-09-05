# Backtest Report: KST (Know Sure Thing) Zero-Line Cross, TrendSpider Periods

**Strategy file:** `strategies/2026-09-06_kst_zero_cross_trendspider.py`
**Date:** 2026-09-06
**Outcome:** ACCEPTED (QQQ only); REJECTED (SPY, crypto)

## Hypothesis

Per TrendSpider's KST Learning Center article, "buy signals are generated
when the KST crosses the zero line", using period set 9/12/18/24 (weighted
x1/x2/x3/x4) — a distinct set from Martin Pring's classic 10/15/20/30 used
by this repo's prior KST entry (2026-09-04-057, rejected, near-miss QQQ,
used signal-line crossover while at/below zero rather than a pure
zero-line cross). This tests the pure zero-cross trigger with
TrendSpider's period set.

Source: https://trendspider.com/learning-center/know-sure-thing/

## Grid test summary (Step 6)

`param_grid={"smooth_window": [6,9,12], "max_hold_days": [10,20,30]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3` (108 cells).

- Overall pass_fraction: **0.222** (24/108)
- By asset class: equity 24/54, **crypto 0/54** (decisive reject)
- By vol regime: low 18/36, mid 3/36, high 3/36 (edge concentrated in
  low-vol, consistent with most prior accepted strategies in this KB)
- Best cell: QQQ, smooth_window=9, max_hold_days=10, low-vol, Sharpe=2.40
- Worst cell: SPY, smooth_window=12, max_hold_days=10, mid-vol,
  Sharpe=-1.10

## Single-config validation (Step 7) — smooth_window=9, max_hold_days=20

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 1.037 — PASS | 0.558 — **FAIL** | >= 1.0 |
| Max drawdown | 0.119 — PASS | (not needed, already failed Sharpe) | <= 0.25 |
| Transaction cost survival (10bps/trade, 49 trades) | 0.923 — PASS | — | >= 0.5 net Sharpe |
| Parameter sensitivity | 0.218 — PASS | — | <= 0.5 |
| Walk-forward | not run — pre-existing `vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt version | — | — |

## Decision

**Accept for QQQ only.** All validators run pass at smooth_window=9,
max_hold_days=20: Sharpe 1.037, max drawdown 0.119, net-of-cost Sharpe
0.923 (49 trades), parameter sensitivity relative_std 0.218 (well within
threshold). **Reject SPY**: full-sample Sharpe 0.558 misses threshold at
the same config (also tried smooth_window=12: SPY still 0.557, no
improvement). **Reject crypto**: 0/54 grid cells passed.

## Notes for future loops

Unlike the previously-rejected Pring-period signal-line-cross KST variant
(2026-09-04-057, near-miss QQQ but rejected outright), this zero-cross +
TrendSpider-period variant clears the bar for QQQ. This is now a live
strategy in `strategies/`. Edge concentrates in low-vol regime (18/36 of
passing cells) consistent with most other accepted momentum/trend
strategies in this repo. SPY consistently underperforms QQQ on KST-family
strategies in this KB (both this entry and the prior Pring-period one) —
worth noting for any future SPY-specific momentum idea that this indicator
family doesn't transfer well to SPY.
