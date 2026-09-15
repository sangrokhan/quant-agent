# 2026-09-15 Trend Detection Index (M.H. Pee) Trend/Consolidation Regime

**Hypothesis:** Per Linn Software's Investor/RT documentation
(https://www.linnsoft.com/techind/trend-detection-index-tdi), M.H. Pee's
Trend Detection Index distinguishes trending markets (TDI>0) from
consolidating ones (TDI<0) using rolling absolute-vs-net momentum;
Direction Indicator (sum of momentum) signals uptrend (>0) vs downtrend
(<0). Source's own disclosed rule: long entry when both TDI and Direction
Indicator are positive. First Trend Detection Index (Pee) entry in this
repo (0 prior matches; not to be confused with the unrelated "Traders
Dynamic Index" sharing the same acronym, already tested several times).

**Primary/best-joint config tried:** momentum_period=28, tdi_period=14,
max_hold_days=60

## Single-config validator results (full 2018-2026 sample)

| Symbol | Sharpe | MDD |
|---|---|---|
| QQQ | 0.034 (**FAIL**, thr 1.0) | 0.185 (pass) |
| SPY | 0.935 (**FAIL** near-miss, thr 1.0) | 0.118 (pass) |

## Grid summary (momentum_period in [14,20,28] x tdi_period in [14,20,28]
x max_hold_days in [30,60], QQQ/SPY/BTC-USDT/ETH-USDT x low/mid/high vol
tercile, 216 cells)

- pass_fraction: 0.185 (40/216)
- by_asset_class: equity 38/108; crypto 2/108
- by_vol_regime: low 32/72; mid 2/72; high 6/72 -- strategy is essentially
  a low-vol-regime-only phenomenon and even there is inconsistent
- No single parameter combo achieves a 3/3-vol-tercile pass on BOTH QQQ
  and SPY simultaneously (best per-symbol combos top out around 2/3 for
  SPY, 1/3 for QQQ) -- the joint full-sample Sharpe check above confirms
  this: QQQ decisively fails (0.034), SPY near-misses (0.935).

## Outcome: REJECTED (both QQQ and SPY on full-sample Sharpe; crypto
decisive fail at grid stage)

The TDI+Direction-Indicator combination, as specified verbatim by the
source, does not produce a robust standalone entry signal on this repo's
equity universe -- it trades far too rarely/erratically (both terms are
simple rolling-sum momentum constructs with no volatility normalization,
so their sign flips are noisy) to clear the Sharpe bar full-sample, despite
some promising per-regime/per-parameter cells in the grid. Not pursuing a
follow-up rescue this cron trigger given the joint-optimum ceiling appears
low (no combo clears both symbols even in the best-case per-regime view).
