# Backtest Report: HalfTrend (everget) Trend-State Gate

**Strategy file:** `strategies/2026-09-17_halftrend_state_gate.py`
**Date:** 2026-09-17
**Hypothesis source:** https://github.com/pradip-interra/PineScripts/blob/main/strategy_ht_ce_pd_rsi_combined.ps (visited this iteration, credits original author "everget")

## Hypothesis

HalfTrend (TradingView user "everget") is a non-repainting ATR-based
trend-flip line. Ported directly from the disclosed Pine Script v5 source:
tracks `SMA(high,amplitude)`/`SMA(low,amplitude)` against
`highest-high`/`lowest-low` over the same `amplitude` window; flips its
internal `trend` state from down(1) to up(0) when
`SMA(low,amplitude) > minHighPrice AND close > prior high` (symmetric for
the down-flip). Source's own disclosed rule: `buySignal = trend==0 and
trend[1]==1` (flip to uptrend), `sellSignal` on the reverse flip.
Implemented long-only as a continuous regime: hold while `trend==0`
(uptrend state), flat while `trend==1` (downtrend state).

## Grid test (Step 6)

`param_grid={amplitude:[2,4,6]}`, `symbols={equity:[QQQ,SPY],
crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01.

- total_cells=36, passed=11 (30.6%)
- by_asset_class: equity 8/18, crypto 3/18
- by_vol_regime: low 9/12, mid 2/12, high 0/12
- best_cell: SPY low-vol amplitude=6, Sharpe=2.81

Per-symbol average-Sharpe-across-regimes best configs: QQQ (amplitude=2,
avg 1.63), SPY (amplitude=6, avg 1.23), BTC/USDT (amplitude=6, avg 1.25),
ETH/USDT (amplitude=6, avg 1.05).

## Single-config validators (Step 7)

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param sens | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | amplitude=2 | 1.422 ✅ | 0.255 ❌ (near-miss, 0.005 over cap) | 1.357 ✅ | 1.00 ✅ | 0.140 ✅ | **near-miss reject** |
| SPY | amplitude=6 | 1.138 ✅ | 0.149 ✅ | 1.103 ✅ | 1.00 ✅ | 0.137 ✅ | **accept** |
| BTC/USDT | amplitude=6 | 0.217 ❌ | 0.465 ❌ | 0.141 ❌ | 1.00 ✅ | 0.145 ✅ | **decisive reject** |
| ETH/USDT | amplitude=6 | 0.190 ❌ | 0.582 ❌ | 0.134 ❌ | 1.00 ✅ | 0.119 ✅ | **decisive reject** |

QQQ was hand-tuned across amplitude∈{2,3,4,5} to find the best MDD/Sharpe
trade-off; amplitude=2 (the grid's own best-avg config) remains the closest
to passing but still exceeds the 0.25 MDD cap by 0.5 percentage points
(0.255). All other amplitudes tested had strictly worse MDD (0.34-0.36).
Recorded as a genuine near-miss (all 4 other validators pass cleanly)
rather than a decisive rejection.

Crypto (BTC/USDT, ETH/USDT) decisively rejected: despite passing at
isolated grid cells, the full-period single config shows very high
turnover (764-793 trades) that erodes returns, MDD nearly 2x the cap on
both.

## Decision (Step 8)

**Accepted** for SPY only (amplitude=6, all 5 validators pass). **Rejected**
QQQ as a near-miss (MDD 0.255 vs 0.25 cap, all other 4 validators pass —
worth revisiting with a smaller amplitude or a vol-scaling overlay in a
future iteration). **Rejected** crypto (BTC/USDT, ETH/USDT — decisive
Sharpe/MDD/TC-survival fail).
