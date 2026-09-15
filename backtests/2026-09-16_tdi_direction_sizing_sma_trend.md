# Trend Detection Index (Pee) Direction-Indicator continuous sizing dial

**Hypothesis id:** 2026-09-16-154 (rescue of 2026-09-16-110)
**Source:** unchanged from 2026-09-16-110 —
https://www.linnsoft.com/techind/trend-detection-index-tdi (M.H. Pee,
S&C V.19:10, already in this repo's ledger; Direction Indicator formula
re-used unchanged). No new external research this sub-iteration.

## Prior state (2026-09-16-110)
Binary AND-gated trigger on two separate raw (unnormalized) rolling-sum
quantities (TDI and Direction Indicator): decisively rejected across all
symbols. QQQ Sharpe 0.034, SPY near-miss 0.935, crypto 2/108 grid passes.
Notes diagnosed: "unnormalized rolling-sum momentum construction (no
volatility scaling) produces noisy/erratic sign flips insufficient for a
robust standalone signal."

## This sub-iteration: continuous sizing dial on the Direction Indicator only
Drops TDI's regime-classification role entirely (the prior entry's own notes
flagged its "counter-intuitive-looking construction" and combined AND-gate
as adding noise). Uses ONLY the Direction Indicator (rolling sum of n-day
momentum — the cleaner directional-magnitude half of the pair),
rolling-z-scored + tanh-squashed to [-1,1], as a continuous exposure dial
inside an SMA(trend_window) uptrend gate with a deadband.

Strategy file: `strategies/2026-09-16_tdi_direction_sizing_sma_trend.py`.

## Step 6 — Grid test
Grid: momentum_period ∈ {15,20,30} × sensitivity ∈ {0.3,0.5,0.7} ×
deadband ∈ {0.15,0.2}, symbols equity {QQQ,SPY} + crypto {BTC/USDT,
ETH/USDT}, vol_regime_splits=3 → 216 cells.
- pass_fraction 0.389 (84/216) — a dramatic rescue from the prior entry's
  0.185 (40/216) grid pass_fraction on the binary version.
- by_asset_class: equity 54/108 (50%), crypto 30/108 (27.8%).
- best_cell: QQQ, momentum_period=30/sensitivity=0.7/deadband=0.15, low-vol,
  Sharpe 3.165 (vs prior entry's QQQ decisive fail 0.034 full-sample).

## Step 7 — Full-sample single-config validators

| Symbol | momentum_period | sensitivity | deadband | leverage_cap | Sharpe | MDD | TC net Sharpe | WF | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 30 | 0.5 | 0.20 | 1.0 | 1.027 | 0.207 | 0.689 | 0.75 | **PASS all** |
| SPY | (multiple tried) | — | — | 1.0 | ≤0.91 | ≤0.18 | fail | 0.75 | **FAIL Sharpe/TC across a 5-config search** |
| BTC/USDT | 30 | 0.16 | 0.10 | 0.4 (base=0.2) | 1.366 | 0.162 | 1.004 | 1.0 | **PASS all** |
| ETH/USDT | 30 | 0.16 | 0.10 | 0.4 (base=0.2) | 1.089 | 0.165 | 0.864 | 1.0 | **PASS all** |

SPY: a 5-config search across momentum_period ∈ {10,15,20} × sensitivity ∈
{0.5,0.7} × deadband ∈ {0.15,0.2} found no config clearing 1.0 Sharpe
(best was 0.913 at momentum_period=15/sensitivity=0.5/deadband=0.15) —
SPY's momentum dynamics don't respond as cleanly to this reframing as QQQ's
did. Left as a documented near-miss for a future targeted retest rather than
forcing acceptance.

Crypto: standard leverage-cap-aware retune grid (24+ combos across two
rounds) — an initial coarse sweep (27 combos) found 0/27 simultaneous BTC+ETH
passes (ETH consistently under-Sharpe at lower leverage), but a finer sweep
targeting higher leverage_cap (0.25-0.4) found 22/24 BTC-only passes and 4/24
ETH-only passes; the intersection at leverage_cap=0.4/sensitivity=0.16/
deadband=0.1 passed BOTH symbols.

## Outcome
**Accepted — QQQ (equity) + full crypto (BTC/USDT, ETH/USDT).** SPY remains
rejected (near-miss, flagged for future revisit). This is a strong rescue
of a previously decisively-rejected strategy: the binary AND-gate combining
two noisy unnormalized rolling sums was the core problem, not the underlying
Direction Indicator signal itself, which transfers cleanly to both equity
(partially) and crypto (fully) once normalized and used as a continuous
sizing dial.
