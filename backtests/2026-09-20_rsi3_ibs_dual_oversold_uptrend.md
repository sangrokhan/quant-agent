# RSI(3) + IBS Dual-Oversold Mean-Reversion in Confirmed Uptrend — QQQ & SPY

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_rsi3_ibs_dual_oversold_uptrend.py`
**Source:** Google AI-overview synthesis of QuantifiedStrategies.com "RSI Trading Strategy for Nasdaq Stocks (Only 17% Drawdown)" — direct article page previously found paywalled in 2026-09-20-072 this same cron trigger; AI-overview now discloses the exact numeric rule.

## Hypothesis

Long entry requires all of: close > SMA(200) (uptrend confirmed); RSI(3) <
20 (short-term oversold); IBS = (Close-Low)/(High-Low) < 0.3 (closed near
the day's low, confirming the oversold reading is not just an
intraday-recovered gap-down). Exit when both IBS > 0.5 and RSI(3) > 50
(reversion confirmed complete). Source's per-stock liquidity/price filters
(50-day avg volume > 10M, price > $25, max 5 positions) omitted as
inapplicable to this repo's single-ETF-symbol daily-bar architecture.

## Grid test (Step 6)

`param_grid={"rsi_threshold": [15, 20, 25], "ibs_threshold": [0.2, 0.3, 0.4]}`,
equity QQQ/SPY + crypto BTC/USDT/ETH/USDT, vol_regime_splits=3, 2019-2026.

- Overall pass fraction: 0.287 (31/108)
- By asset class: **equity 31/54 (0.574)**, crypto 0/54 (0.0, decisive reject)
- By vol regime: low 18/36, mid 3/36, high 10/36
- Best cell: rsi_threshold=20, ibs_threshold=0.2, SPY, low-vol regime, Sharpe 2.65

## Single-config validation (Step 7) — rsi_threshold=20, ibs_threshold=0.3

| Symbol | Sharpe | MDD | Net-of-cost Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| **QQQ** | **1.203 (PASS)** | **0.110 (PASS)** | **1.057 (PASS)** | **1.0 (PASS)** | **0.071 (PASS)** |
| **SPY** | **1.140 (PASS)** | **0.088 (PASS)** | **0.947 (PASS)** | **0.75 (PASS)** | **0.114 (PASS)** |

**Both QQQ and SPY pass all 5 validators** — a full equity-universe accept
with very low parameter sensitivity (relative_std 0.07-0.11, among the
lowest of any strategy this cron trigger), indicating a robust edge.

## Decision: **ACCEPTED for equity (QQQ AND SPY)**, rsi_threshold=20, ibs_threshold=0.3

Rejected/out-of-scope: crypto BTC/USDT and ETH/USDT (0/54 grid cells pass
decisively — the dual-oversold-in-uptrend construction does not translate
to crypto's noisier daily bars in this repo's data).
