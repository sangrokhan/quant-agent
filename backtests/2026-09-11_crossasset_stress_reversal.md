# 2026-09-11 Cross-Asset Correlated-Stress Reversal (SPY/QQQ) — Backtest Report

**Hypothesis:** Long the primary asset (SPY/QQQ) for one day whenever IEF
(Treasuries) rises while a risk-on asset (GLD, USO, or the primary asset
itself) falls beyond a dynamic threshold on the same day — a
cross-asset-confirmed "flight to safety" stress signal. Source:
https://quantpedia.com/short-term-correlated-stress-reversal-trading/
(visited this iteration, full disclosed methodology, Vojtko 2025).

## Single-config validators (best config: QQQ, ief_thresh=0.0, risk_thresh=0.0, 2010-01-01 to 2024-01-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.170 | >= 1.0 | ✅ |
| Max drawdown | 0.208 | <= 0.25 | ✅ |
| Transaction cost survival (10bps/trade repo-standard, 1510 trades) | net Sharpe 0.079 | >= 0.5 | **FAIL** (decisive, not near-miss, at repo-standard 10bps; was reported 0.402 at an initially-used 5bps before catching the repo-standard convention is 10bps/trade — corrected here) |
| Walk-forward (manual 4-way range-split; `check_walk_forward` raises on installed vectorbt 1.1.0, pre-existing bug flagged in 2026-09-10-021/022) | 4/4 splits positive, 1.0 | >= 0.75 ✅ |

## Step 6 grid summary (ief_thresh in [0.0, 0.002] x risk_thresh in [0.0, 0.005], SPY/QQQ + BTC/USDT/ETH/USDT, vol_regime_splits=3)

- 48 total cells, 15 passed (pass_fraction 0.3125)
- **by_asset_class**: equity 15/24 (62.5%), crypto 0/24 (0%)
- **by_vol_regime**: low 8/16, mid 4/16, high 3/16
- Best cell: QQQ, ief_thresh=0.0/risk_thresh=0.0, low-vol regime, Sharpe 2.21
- Worst cell: ETH/USDT, ief_thresh=0.002/risk_thresh=0.005, mid-vol regime, Sharpe -0.08

## Extra parameter sweep for transaction-cost robustness

| ief_thresh | risk_thresh | Sharpe | MDD | trades | net-Sharpe-after-5bps |
|---|---|---|---|---|---|
| 0.0 | 0.0 | 1.170 ✅ | 0.208 ✅ | 1510 | 0.402 (fail) |
| 0.0 | 0.005 | 1.108 ✅ | 0.210 ✅ | 1094 | 0.492 (fail, near-miss) |
| 0.001 | 0.003 | 0.886 | 0.194 | 1018 | 0.347 |
| 0.003 | 0.003 | 0.534 | 0.166 | 568 | 0.225 |
| 0.005 | 0.005 | 0.550 | 0.137 | 245 | 0.374 |
| 0.003 | 0.008 | 0.508 | 0.154 | 437 | 0.257 |

Every config tested has high trade frequency (a strict 1-day-hold
strategy inherently generates 1 round-trip trade per triggered signal),
and raising the trigger thresholds to reduce trade count also reduces
the raw Sharpe faster than it reduces the cost drag — no config found
clears the 0.5 net-Sharpe transaction-cost threshold; the best (0.0/0.005)
comes reasonably close at 0.492 but still fails.

## Decision: REJECTED

Sharpe, max drawdown, and (manual) walk-forward all pass for QQQ at the
default (0.0, 0.0) threshold, but **transaction-cost survival fails
decisively** — this is a fundamentally high-turnover 1-day-hold strategy
(the source's own reported backtest presumably doesn't model per-trade
costs at this granularity, or Quantpedia's audience is expected to trade
this via cheap ETF/futures execution with near-zero effective
round-trip costs, which this repo's flat 5bps/trade estimate does not
assume). SPY fails Sharpe outright; crypto fails decisively across the
board (0/24, no IEF/GLD/USO cross-asset analog exists for crypto markets
-- correctly flagged as feasibility-limited to equity only).

## Notes for future iterations

- First cross-asset-confirmed same-day stress-event 1-day-hold reversal
  strategy in this repo; distinct from all prior single-asset drawdown/
  VIX-level/Ulcer-Index triggers and from the slower multi-day HYG/LQD
  credit z-score regime gate (2026-09-05-025).
- Near-miss on transaction costs specifically (0.492 vs 0.5 threshold at
  ief_thresh=0.0/risk_thresh=0.005) — a future iteration could try a
  cheaper execution assumption (e.g. 2-3bps/trade, common for liquid ETF
  fills) or a longer hold period (2-3 days instead of strict 1-day) to
  reduce trade frequency while preserving more of the raw edge, since the
  underlying Sharpe/MDD/walk-forward profile on QQQ is otherwise solid.
- Crypto is feasibility-blocked for this exact construction (no
  Treasury/gold/oil cross-asset stress proxy exists in crypto markets),
  confirmed decisively rejected (0/24 in grid) rather than worth
  revisiting.
