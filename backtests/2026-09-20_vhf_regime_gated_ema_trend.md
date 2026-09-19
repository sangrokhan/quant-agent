# Vertical Horizontal Filter (VHF, Adam White) Regime-Gated EMA Trend — QQQ

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_vhf_regime_gated_ema_trend.py`
**Source:** Google AI-overview synthesis (TrendSpider/cTrader/Incredible Charts)

## Hypothesis

VHF(28) = (HighestClose - LowestClose) / sum(|Close_i - Close_i-1|) is a
direction-blind trend-vs-range regime detector (Adam White). Long entry
when VHF > threshold (trending regime confirmed) AND close crosses above a
baseline EMA (direction trigger); exit when close crosses back below the
EMA.

## Grid test (Step 6)

`param_grid={"vhf_threshold": [0.25, 0.35, 0.45], "ema_period": [20, 40, 60]}`,
equity QQQ/SPY + crypto BTC/USDT/ETH/USDT, vol_regime_splits=3, 2019-2026.

- Overall pass fraction: 0.352 (38/108)
- By asset class: equity 24/54 (0.444), crypto 14/54 (0.259)
- By vol regime: low 27/36 (0.75), mid 11/36 (0.306), high 0/36 (0.0) — decisive high-vol failure
- Best cell: vhf_threshold=0.35, ema_period=40, QQQ, low-vol regime, Sharpe 3.02

## Single-config validation (Step 7) — vhf_threshold=0.35, ema_period=40

| Symbol | Sharpe | MDD | Net-of-cost Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| **QQQ** | **1.252 (PASS)** | **0.187 (PASS)** | **1.215 (PASS)** | **0.75 (PASS)** | **0.199 (PASS)** |
| SPY | 0.204 (FAIL) | 0.272 (FAIL) | 0.142 (FAIL) | 0.75 (pass) | 0.628 (FAIL) |
| BTC/USDT | 0.137 (FAIL) | 0.464 (FAIL) | 0.044 (FAIL) | 1.0 (pass) | 0.263 (pass) |
| ETH/USDT | 0.173 (FAIL) | 0.654 (FAIL) | 0.086 (FAIL) | 0.75 (pass) | 0.156 (pass) |

**QQQ passes all 5 validators.** SPY and crypto fail decisively on
Sharpe/MDD/tx-cost-survival — crypto in particular generates 900+ trades
(vs QQQ's 23), incurring massive transaction-cost drag (net Sharpe collapses
to 0.04-0.09) and catastrophic drawdowns (46-65%).

## Decision: **ACCEPTED for QQQ only** (vhf_threshold=0.35, ema_period=40)

Rejected/out-of-scope: SPY (fails Sharpe, MDD, tx-cost, param-sensitivity);
crypto BTC/USDT and ETH/USDT (fail Sharpe, MDD decisively — 46-65% max
drawdown, and tx-cost survival collapses due to extremely high trade
frequency on crypto's noisier daily bars under this VHF/EMA parameterization).
Do not extend to SPY or crypto without a fundamentally different
threshold/period recalibration in a future iteration.
