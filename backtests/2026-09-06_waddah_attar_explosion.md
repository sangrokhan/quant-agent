# Backtest Report: Waddah Attar Explosion (WAE)

**Strategy file:** `strategies/2026-09-06_waddah_attar_explosion.py`
**Date:** 2026-09-06
**Outcome:** REJECTED

## Hypothesis

Per LuxAlgo's Waddah Attar Explosion library page: "trend power" (bar-to-bar
change of a 20/40 EMA MACD line * sensitivity 150) gated by both an
"explosion line" (width of 20-period, 2-std Bollinger Bands) and an
ATR(100)*3.7 "dead zone" noise floor. Long entry requires trend power
positive AND clearing both gates simultaneously ("Column breaks above the
explosion line ... the go condition"; "Color flip: green permits longs").
Novel indicator family for this repo.

Source: https://www.luxalgo.com/library/indicator/waddah-attar-explosion/

## Grid test summary (Step 6)

`param_grid={"atr_mult": [2.5,3.7,5.0], "max_hold_days": [10,15,25]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3` (108 cells).

- Overall pass_fraction: **0.343** (37/108) — highest raw grid pass-rate
  of any strategy tested this run
- By asset class: equity 37/54, **crypto 0/54** (decisive reject)
- By vol regime: low 17/36, mid 18/36, high 2/36
- Best cell: QQQ, atr_mult=5.0, max_hold_days=10, mid-vol, Sharpe=1.95
- SPY at atr_mult=2.5 or 3.7, max_hold_days=10 passed all 3/3 vol regimes
  in the grid (grid_test's own internal pass criteria, which does not
  penalize trade frequency)

## Single-config validation (Step 7) — atr_mult=3.7, max_hold_days=10

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.866 — **FAIL** | 1.075 — PASS | >= 1.0 |
| Max drawdown | 0.153 — PASS | 0.118 — PASS | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.312 — **FAIL** (282 trades) | 0.268 — **FAIL** (302 trades) | >= 0.5 net Sharpe |
| Parameter sensitivity | 0.025 — PASS | 0.080 — PASS | <= 0.5 |

Tried additional configs (atr_mult=5.0, max_hold_days=25/15) to reduce
trade frequency — trade counts stayed at 240-264, cost survival still
failed decisively (net Sharpe 0.19-0.39) for both symbols.

## Decision

**Reject.** The grid's per-cell Sharpe looks attractive (the indicator's
"go/no-go gate" nature makes it a fine timing filter in isolated windows),
but the signal fires far too frequently (240-300+ round trips over the
sample vs. 20-100 for most other strategies in this KB) — transaction
costs at a realistic 10bps/trade estimate overwhelm the raw edge on both
QQQ and SPY across every config tried. Crypto rejected decisively (0/54
grid cells).

## Notes for future loops

The underlying momentum-vs-volatility-envelope logic may still have merit
with an added minimum-hold or cooldown mechanism (similar to
2026-09-04-085's fix for Klinger Volume Oscillator's overtrading problem)
to cut trade frequency without changing the entry logic itself — worth
revisiting with an explicit `min_hold_days` gate in a future loop rather
than abandoning the indicator family outright.
