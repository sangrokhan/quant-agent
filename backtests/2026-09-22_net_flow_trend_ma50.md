# Net Flow Trend (Windowed, Volume-Normalized OBV) + MA50 Cross Confirmation

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_net_flow_trend_ma50.py`
**Outcome:** ACCEPTED (QQQ only)

## Hypothesis + Source

Per ChartCrypto.app's "Net Flow Trend" backtesting strategy page
(https://chartcrypto.app/backtesting/net-flow-trend): FLOW is a windowed
On-Balance-Volume variant -- each bar contributes +volume when it closes up
and -volume when it closes down, summed over a rolling `flow_window` (20)
bars and normalized by the average volume over that same window (bounded,
comparable across symbols, unlike raw cumulative OBV).

Source's disclosed rule: "The entry is a 50-bar moving-average break
confirmed by FLOW > 0.5 ... The exit mirrors it -- the MA50 cross down or
FLOW collapsing below -0.5."

First strategy in this repo using a rolling-window, volume-normalized net
flow value against a fixed threshold (distinct from existing cumulative-OBV
family entries: 2026-09-04-027, 2026-09-04-088, 2026-09-05-060, 2026-09-05-078).

## Grid summary (108 cells: flow_window in [10,20,30] x flow_entry_threshold
in [0.3,0.5,0.7] x equity[QQQ,SPY]/crypto[BTC,ETH] x 3 vol terciles)

- pass_fraction: 0.352 (38/108)
- by_asset_class: equity 27/54, crypto 11/54
- by_vol_regime: low 27/36, mid 11/36, high 0/36 (edge concentrated in
  low/mid volatility; strategy does not hold up in high-vol regimes)
- Best cell: QQQ flow_window=30/flow_entry_threshold=0.5/low-vol Sharpe 2.90
- Best full-sample config by average multi-regime Sharpe: QQQ
  flow_window=20/flow_entry_threshold=0.5/ma_window=50, avg Sharpe 1.57
  across the 2 passing regimes (low, mid)

## Single-config validation (flow_window=20, ma_window=50,
flow_entry_threshold=0.5, flow_exit_threshold=-0.5, max_hold_days=60)

| Symbol | Sharpe | MDD | TC-net Sharpe | Walk-fwd | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.494 (PASS) | 0.137 (PASS) | 1.244 (PASS) | 1.0 (PASS) | 0.142 rel_std (PASS) | **ALL 5 PASS -- ACCEPTED** |
| SPY | 1.020 (PASS) | 0.148 (PASS) | 0.704 (PASS) | 1.0 (PASS) | 28.13 rel_std (FAIL) | Rejected -- fragile across neighboring grid cells (mean sharpe ~0 across grid, sign-flipping) |
| BTC/USDT (1h bars) | 0.231 (FAIL) | 0.440 (FAIL) | -0.023 (FAIL) | 1.0 (PASS) | 0.027 rel_std (PASS) | Decisively rejected -- massive over-trading (5657 position changes) at hourly granularity, cost-survival fails |

## Decision

**Accepted for QQQ only.** All 5 standard validators pass cleanly (Sharpe
1.49, MDD 13.7%, TC-net-Sharpe 1.24, walk-forward 4/4 splits positive,
parameter-sensitivity rel_std 0.142 -- among the tightest/most stable of
any strategy tested this cron trigger). SPY at the identical config passes
Sharpe/MDD/TC/walk-forward but fails parameter-sensitivity badly (near-zero
mean Sharpe across the flow_window/threshold grid neighborhood, meaning the
QQQ result at this specific config could be a lucky point for SPY). Crypto
(BTC/USDT) fails decisively due to over-trading at 1h bar granularity and a
high-vol-regime concentration failure visible in the grid (0/36 high-vol
cells pass across the whole grid).

Scope: this strategy is validated and accepted for QQQ (Nasdaq-100 ETF)
only. Do not assume it generalizes to SPY or crypto without further
retuning/regime-gating in a future iteration.
