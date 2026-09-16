# LWMA Distance Continuous Sizing Dial — Backtest Report

**Date:** 2026-09-17
**Strategy file:** `strategies/2026-09-17_lwma_dist_sizing_dual_window.py`
**Hypothesis:** Linear-Weighted Moving Average (LWMA) — dual-window
construction (short LWMA for mean-reversion dip detection, long LWMA as a
trend gate) reframed as a continuous sizing dial (distance from short LWMA,
rolling z-scored + tanh, inverted sign for mean-reversion), gated by
close > long LWMA. First LWMA strategy in this repo.

**Source:** https://www.quantifiedstrategies.com/linear-weighted-moving-average/
(read via browser_exec this iteration; source's own SPY backtest tables show
short LWMA windows favor mean-reversion, long windows favor trend-following
— basis for this dual-window construction).

## Step 6 grid summary (432 cells: short_lwma_window x{5,10,20},
long_lwma_window x{80,100,150}, sensitivity x{0.5,0.7}, deadband x{0.15,0.2},
2 equity + 2 crypto symbols, vol_regime_splits=3)

- Overall pass_fraction: **0.2708** (117/432)
- By asset class: equity 83/216 (0.384); crypto 34/216 (0.157)
- By vol regime: low 92/144 (0.639); mid 25/144 (0.174); high **0/144 (0.0)**
  — same categorical high-vol-regime failure pattern seen in several other
  recent continuous-sizing-dial strategies this cron trigger.
- Best cell: QQQ, short_lwma_window=20/long_lwma_window=150/sensitivity=0.5/
  deadband=0.2, low-vol regime, Sharpe 2.06.
- Worst cell: QQQ, short_lwma_window=20/long_lwma_window=100/sensitivity=0.5/
  deadband=0.2, high-vol regime, Sharpe -0.91.

Best-average-Sharpe config per symbol:
- QQQ: short=10/long=80/sensitivity=0.5/deadband=0.20 → avg Sharpe 0.985, pass_frac 0.667
- SPY: short=5/long=80/sensitivity=0.5/deadband=0.20 → avg Sharpe 0.975, pass_frac 0.667
- BTC/USDT: short=5/long=80/sensitivity=0.5/deadband=0.15 → avg Sharpe 0.874, pass_frac 0.333
- ETH/USDT: short=5/long=80/sensitivity=0.5/deadband=0.20 → avg Sharpe 1.057, pass_frac 0.0 (regime-cell-level fails despite decent averaged Sharpe)

## Step 7 single-config validators (best-per-symbol config; crypto retuned to
leverage_cap=0.3, base_exposure=0.15)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 0.915 (fail, narrow miss) | 0.116 (pass) | 0.016 (fail) | 0.75 (pass) | 0.016 rel-std (pass) | NO |
| SPY | 0.934 (fail, narrow miss) | 0.109 (pass) | -0.152 (fail) | 1.0 (pass) | 0.097 rel-std (pass) | NO |
| BTC/USDT | 0.248 (fail) | 0.092 (pass) | -0.069 (fail) | 1.0 (pass) | 0.052 rel-std (pass) | NO |
| ETH/USDT | 0.255 (fail) | 0.139 (pass) | -0.067 (fail) | 1.0 (pass) | 0.111 rel-std (pass) | NO |

## Decision

**Rejected across the full universe (QQQ, SPY, BTC/USDT, ETH/USDT).** Both
equity symbols are close-but-decisive near-misses on full-sample Sharpe
(0.915/0.934, both <1.0) and fail transaction-cost survival due to elevated
turnover (474-597 trades over the sample) relative to the thin Sharpe edge —
the mean-reversion dip-buying leg appears to generate too many marginal
trades for the net edge to survive 10bps/trade costs. Crypto fails
decisively even after the standard leverage-cap retune (elevated turnover,
9-10k trades over the sample — the short_lwma_window=5 dual-window
construction is far too reactive on crypto's 24/7 calendar).

**Notable finding for future loops:** QQQ and SPY are both narrow Sharpe
near-misses (0.915, 0.934) that fail primarily on the transaction-cost
validator, not the Sharpe/MDD/walk-forward validators. A future iteration
could retry with a wider deadband (to cut turnover) or a longer short_lwma
window (to reduce whipsaw) as a targeted TC-survival fix, following this
repo's established near-miss rescue pattern. Also reconfirms the
categorical high-vol-regime failure pattern already flagged in this cron
trigger's 2026-09-17-104 (VPT) entry — likely a shared weakness of the
deadband + z-score-tanh dial + SMA/LWMA trend-gate mechanic under this
repo's transaction-cost model during high-vol periods, worth investigating
as a standalone meta-finding in a future iteration.
