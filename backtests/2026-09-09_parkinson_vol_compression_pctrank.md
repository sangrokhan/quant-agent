# Parkinson Volatility Compression Percentile-Rank Mean Reversion — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_parkinson_vol_compression_pctrank.py`
**Source:** Follow-up to this cron trigger's 2026-09-09-027 (Parkinson vol
expansion-cross, decisively rejected); same TradingView "Parkinson Range
Oscillator [BackQuant]" source (kr.tradingview.com mirror), using the
script's percentile-rank component instead of its EMA-cross component.

## Hypothesis

2026-09-09-027's own notes suggested trying the oscillator's
percentile-rank form instead of the EMA-signal-line expansion-cross, since
the cross condition was too rare (6-11 trades/7.7yr). This iteration tests
a distinct mean-reversion construction: low Parkinson-vol percentile rank
(`pctRank <= compression_pctrank`, historically quiet intrabar range) as a
standalone long-entry trigger with a fixed time-stop exit, on the intuition
that unusually compressed volatility periods precede reversion.

## Grid test (Step 6)

`compression_pctrank ∈ {10, 15, 20}` x `max_hold_days ∈ {5, 10}` x {QQQ,
SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 72 cells.

- **pass_fraction: 0.153** (11/72)
- by_asset_class: equity 11/36, crypto 0/36 (decisive fail)
- by_vol_regime: low 11/24 only, mid/high 0/24
- best_cell: SPY, low-vol, `compression_pctrank=20, max_hold_days=5`, Sharpe 2.12

## Single-config validation (best config: `compression_pctrank=20, max_hold_days=5`)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.727 (FAIL) | 0.200 (FAIL, decisive) | ≥ 1.0 |
| Max drawdown | 0.182 (PASS) | 0.161 (PASS) | ≤ 0.25 |
| Net Sharpe after costs | 0.504 (PASS, borderline) | -0.045 (FAIL, negative) | ≥ 0.5 |

Trade counts: QQQ 101, SPY 104 — much higher frequency than the
expansion-cross version, confirming the percentile-rank trigger fires
often, but the higher frequency did not translate into edge; SPY's net
Sharpe after costs is negative.

## Decision: REJECTED

Full-sample Sharpe misses the 1.0 threshold on both QQQ (0.727) and SPY
(0.200, essentially a coin-flip), with SPY's net-of-cost Sharpe actually
negative. As with the expansion-cross predecessor, the grid's isolated
low-vol-tercile best cell (Sharpe 2.12) does not survive full-sample
testing. Both Parkinson-volatility-based constructions tested this cron
trigger (expansion-cross trend-following and compression-percentile-rank
mean-reversion) failed decisively — no further variant of this indicator
family is recommended without a substantially different signal
construction or entry/exit mechanism.
