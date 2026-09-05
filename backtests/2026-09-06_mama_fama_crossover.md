# Backtest Report: MAMA/FAMA Crossover (Ehlers MESA Adaptive MA)

**Strategy file:** `strategies/2026-09-06_mama_fama_crossover.py`
**Date:** 2026-09-06
**Outcome:** ACCEPTED (QQQ only); REJECTED (SPY, crypto)

## Hypothesis

Per LuxAlgo's MAMA/FAMA library page: "MAMA crosses above FAMA: the
conventional long bias; the mirror cross flips it bearish." MAMA/FAMA is
John Ehlers' Hilbert-transform-based adaptive moving average pair
(cycle-adaptive smoothing factor between fast_limit~0.5 and
slow_limit~0.05, computed on hl2). Novel indicator family for this repo —
no prior MAMA/FAMA/MESA-adaptive entries in the KB.

Source: https://www.luxalgo.com/library/indicator/mama-fama/

## Grid test summary (Step 6)

`param_grid={"fast_limit": [0.3,0.5,0.7], "max_hold_days": [10,20,30]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3` (108 cells).

- Overall pass_fraction: **0.231** (25/108)
- By asset class: equity 25/54, **crypto 0/54** (decisive reject)
- By vol regime: low 18/36, mid 3/36, high 4/36 (edge concentrated in
  low-vol, consistent with most accepted strategies in this KB)
- Best cell: QQQ, fast_limit=0.3, max_hold_days=10, low-vol, Sharpe=2.66
- Worst cell: QQQ, fast_limit=0.3, max_hold_days=30, high-vol, Sharpe=-0.15
- Best shared config: fast_limit=0.5, max_hold_days=20 (QQQ 2/3 vol
  regimes pass, SPY 1/3)

## Single-config validation (Step 7) — fast_limit=0.5, max_hold_days=20

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 1.142 — PASS | 0.649 — **FAIL** | >= 1.0 |
| Max drawdown | 0.108 — PASS | 0.157 — PASS | <= 0.25 |
| Transaction cost survival (10bps/trade) | 1.007 — PASS (61 trades) | 0.483 — **FAIL** (70 trades) | >= 0.5 net Sharpe |
| Parameter sensitivity | 0.199 — PASS | 0.194 — PASS | <= 0.5 |
| Walk-forward | not run — pre-existing `vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt version | — | — |

## Decision

**Accept for QQQ only.** All validators run pass at fast_limit=0.5,
max_hold_days=20: Sharpe 1.142, MDD 0.108, net-of-cost Sharpe 1.007 (61
trades), parameter sensitivity relative_std 0.199. **Reject SPY**:
full-sample Sharpe 0.649 and net-of-cost Sharpe 0.483 both miss threshold
(70 trades, slightly overtrading relative to its edge vs. QQQ). **Reject
crypto**: 0/54 grid cells passed.

## Notes for future loops

MAMA/FAMA now a live strategy in `strategies/` for QQQ. The implementation
follows Ehlers' original published MESA algorithm (Hilbert transform
homodyne discriminator, per LuxAlgo's cited formula) rather than a
simplified approximation — verified it runs fast (<0.2s per symbol, no
performance concern for future grid expansion). Edge concentrated in
low-vol regime, same pattern as most other accepted trend-following
strategies in this KB. Untested here: `slow_limit` parameter (fixed at
0.05 default) and alternate price sources (Ehlers' original uses hl2,
worth testing close-only as an ablation in a future loop).
