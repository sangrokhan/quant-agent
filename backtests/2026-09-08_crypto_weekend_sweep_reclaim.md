# Backtest Report: Crypto Weekend Sweep-and-Reclaim Breakout

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_crypto_weekend_sweep_reclaim.py`
**Source:** https://voiceofchain.com/academy/weekend-crypto-trading-strategy

## Hypothesis

Per the source, crypto weekend liquidity is thin, so price often sweeps a
visible weekend range extreme before reclaiming it: "identify Friday close
range, wait for a weekend sweep, enter only after reclaim." Source is
intraday (15m); adapted to a daily-bar analog: weekend range = high/low of
Sat+Sun daily bars; sweep = Monday's low dips below that range low; reclaim
= Monday's close ends back above it -- long entry on that combination.
Crypto-only (no equity weekend bars). Distinct from the already-rejected
static Friday-close-to-Monday-close calendar HOLD (2026-09-04-029) since
this requires an actual sweep+reclaim price-structure condition, not an
unconditional hold.

## Grid Test Summary (param_grid: max_hold_days=[3,5,10]; symbols
BTC-USDT/ETH-USDT only (crypto-only strategy); vol_regime_splits=3;
2019-01-01 to 2026-09-01)

- total_cells: 18, passed: 0, **pass_fraction: 0.0** (decisive)
- best_cell Sharpe only 0.214 (ETH, mid-vol, max_hold_days=3) -- no cell
  clears the 1.0 threshold at all
- by_vol_regime: low 0/6, mid 0/6, high 0/6

## Single-Config Full-Period Check (max_hold_days=5, 2019-2026)

| Symbol | Trades | Full-period Sharpe |
|---|---|---|
| BTC/USDT | 30 | -0.035 (decisive FAIL) |
| ETH/USDT | 23 | -0.035 (decisive FAIL) |

Reasonable sample size (23-30 trades over 7.7yr), clean decisive rejection
-- essentially zero edge (Sharpe near zero, not just below threshold).

## Decision: **REJECT**

The daily-bar analog of the source's intraday sweep-and-reclaim mechanism
produces no edge at all (Sharpe ~0 on both BTC and ETH). This is not
surprising given the source's own mechanism depends on 15-minute
sweep/reclaim precision and funding-rate/open-interest microstructure
signals that a daily-bar reconstruction cannot capture -- the "weekend
thin liquidity" effect described likely only manifests at intraday
resolution, not as a next-day daily-close pattern.
