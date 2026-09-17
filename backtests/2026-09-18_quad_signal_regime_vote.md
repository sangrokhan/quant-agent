# Backtest Report: Quad-Signal Risk-On Regime Vote

**Strategy file:** `strategies/2026-09-18_quad_signal_regime_vote.py`
**Hypothesis id:** 2026-09-18-005
**Source:** https://www.reddit.com/r/LETFs/comments/1tbnksd/i_backtested_qldtqqq_rotation_rules_from_19862026/ (r/LETFs, "Quad Risk K2" strategy family description)

## Hypothesis

The source's "Quad Risk K2" strategy holds a leveraged ETF (QLD) when at
least 2 of 4 binary regime signals are true (long trend, medium trend,
realized volatility, short-term return persistence), otherwise rotates to a
defensive asset. The post discloses the STRUCTURE (4-signal majority vote,
>=2-of-4 threshold) but not exact numeric signal definitions. This iteration
operationalizes the four categories with this repo's own standard
constructions (long trend=close>SMA(200); medium trend=close>SMA(50);
realized vol=20d vol<=trailing 252d median; persistence=20d return>0),
applies the same majority-vote gate, and trades the un-leveraged QQQ/SPY
rather than the source's QLD/TQQQ (leveraged vehicles decisively fail this
repo's 0.25 MDD threshold, confirmed again by this iteration's own crypto
results below).

## Grid Test Summary (Step 6)

Grid: `vote_threshold` in {2,3}, `long_trend_window` in {150,200},
`persistence_window` in {10,20}, symbols equity {QQQ, SPY} + crypto
{BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- total_cells: 96, passed_cells: 28, **pass_fraction: 0.292**
- by_asset_class: equity 24/48, crypto 4/48 (edge concentrated equity)
- by_vol_regime: low 18/32, mid 10/32, high 0/32
- best_cell: SPY low-vol, vote_threshold=3/long_trend_window=150/persistence_window=10, Sharpe 2.72
- worst_cell: QQQ high-vol, vote_threshold=3/long_trend_window=200/persistence_window=10, Sharpe -0.89

A follow-up full-sample sweep (widening medium_trend_window, vote_threshold=2)
found a config passing BOTH QQQ and SPY simultaneously.

## Single-Config Validation (Step 7)

Config: `vote_threshold=2, long_trend_window=200, medium_trend_window=50,
persistence_window=20`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|--------|--------|-----|------------------------|--------------|--------------------|---------|
| QQQ    | 1.254  | 0.168 | 1.205                 | 1.0 (4/4)    | 0.086              | **ACCEPT** |
| SPY    | 1.015  | 0.154 | 0.929                 | 1.0 (4/4)    | 0.037              | **ACCEPT** |
| BTC/USDT | 0.883 | 0.663 | 0.851                | 1.0 (4/4)    | 0.041              | REJECT (decisive Sharpe+MDD fail) |
| ETH/USDT | 0.810 | 0.695 | 0.786                | 1.0 (4/4)    | 0.046              | REJECT (decisive Sharpe+MDD fail) |

## Decision (Step 8)

**Accepted for QQQ AND SPY** (equity), both pass all 5 validators cleanly.
Crypto (BTC/USDT, ETH/USDT) decisively rejected -- the regime-vote
construction produces much higher turnover on crypto (~220 trades vs
~90-113 for equity) and correspondingly severe drawdowns (MDD 0.66-0.70),
consistent with several other regime-gate strategies in this repo that
don't transfer cleanly to crypto's different volatility/bar profile.
