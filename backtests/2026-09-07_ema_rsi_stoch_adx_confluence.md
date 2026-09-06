"""Backtest report: EMA(34/89)+RSI(3)+Stochastic+ADX confluence.

Hypothesis id: 2026-09-07-024
Strategy file: strategies/2026-09-07_ema_rsi_stoch_adx_confluence.py
Outcome: **REJECTED**

## Hypothesis

Per a widely-circulated Forex-education rule set (Facebook/Course Hero,
identical wording across >=3 independent sources): a long entry requires
FOUR simultaneous conditions -- 34EMA>89EMA (Fibonacci-period trend
filter), fast 3-period RSI crossing above 80 (momentum thrust, not
overbought-exhaustion since 3-period RSI is far noisier than the repo's
existing RSI(2)/RSI(14) variants), Stochastic %K>%D (bullish persistence),
and ADX +DI>-DI (directional confirmation). Exit on any condition
reversing, or a max_hold_days time-stop backstop (source specifies none).

## Step 6 grid summary (rsi_thresh in [75,80,85] x max_hold_days in
[10,15], symbols QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- total_cells: 72, passed_cells: 10, pass_fraction: **0.139**
- by_asset_class: equity 10/36 (0.278), crypto 0/36 (0.0, decisive)
- by_vol_regime: low 0/24 (0.0), **mid 10/24 (0.417)**, high 0/24 (0.0)
  -- unusual pattern, all passes concentrated in the MID-vol tercile only
  (neither low nor high vol), suggesting a narrow regime-specific
  artifact rather than a genuine edge
- best_cell: QQQ, rsi_thresh=80, max_hold_days=10, mid-vol regime,
  Sharpe 2.079

## Step 7 single-config validation (rsi_thresh=80, max_hold_days=10, full
2019-2026 sample, QQQ & SPY)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.461 (FAIL) | 0.335 (FAIL) | >= 1.0 |
| Max drawdown | 0.109 (PASS) | 0.059 (PASS) | <= 0.25 |
| Tx-cost survival (5bps, 155/154 trades) | 0.204 (FAIL) | 0.001 (FAIL) | >= 0.5 net Sharpe |
| Walk-forward | not run -- decisive full-sample failure, plus pre-existing `vbt.utils.splitting` AttributeError bug | | |
| Parameter sensitivity | not run -- decisive full-sample failure already conclusive | | |

## Decision

**Rejected.** Full-sample Sharpe and transaction-cost survival both fail
decisively for both QQQ and SPY. The very high trade count (154-155
trades over 7.7yr, roughly one every 2-3 weeks) is the key structural
problem: this 4-way AND-gate, despite being restrictive on paper, still
fires frequently enough that round-trip transaction costs (5bps/trade)
completely erase the strategy's edge (net Sharpe collapses to
essentially zero, 0.001-0.204 vs the 0.5 threshold). The grid's
pass_fraction was concentrated entirely in the mid-vol regime tercile
(10/24) with zero passes in low- or high-vol regimes -- a pattern
consistent with a narrow, non-generalizing artifact rather than a real
edge, and MDD passing cleanly (10.9%/5.9%) mainly reflects a strategy
that is flat most of the time between its frequent, small, largely
cost-eroded trades rather than genuine risk control. Crypto rejected
categorically (0/36 grid cells).

Source: multiple identical Facebook trading-education posts (e.g.
AsiaForexMentor.com's "exact setup" reel) and a Course Hero-hosted
"Trading strategies collection.pdf", cross-confirmed via Google search
result snippets (informal distribution channel, but the exact rule text
"The 34 EMA must be above the 89 EMA. The 3 RSI must cross above the 80
level. The Stochastic must be above its Signal line." appears verbatim
across independent sources, so treated as a genuine reproducible rule).
"""
