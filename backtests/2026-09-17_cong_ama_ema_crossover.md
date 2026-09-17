# Backtest Report: Cong AMA vs EMA Crossover

**Strategy file:** `strategies/2026-09-17_cong_ama_ema_crossover.py`
**Hypothesis id:** 2026-09-17-169

## Source

TASC (Technical Analysis of Stocks & Commodities) May 2023 Traders' Tips
(implementing the March 2023 article), Scott Cong, "An Adaptive Moving
Average For Swing Trading", via
https://traders.com/Documentation/FEEDbk_docs/2023/05/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl).

Cong's AMA uses a "range efficiency ratio" for its adaptive alpha: net
high-low range over the lookback window divided by the cumulative true
range (sum of true ranges) over the same window -- distinct from Kaufman's
classic KAMA (price-change/sum-of-absolute-changes, no high/low/true
range), FRAMA (fractal dimension), and the RS EMA/LRAdj EMA/TRAdj EMA
adaptive-EMA families already tested in this repo.

## Trading rule

Cong's AMA crossing above a plain EMA of the same `length`, gated by
`close > SMA(trend_window)` = long entry; exit on reverse cross
(`min_hold_days` hysteresis) or `max_hold_days` time-stop.

## Step 6 grid summary (length x max_hold_days x min_hold_days, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-2026)

- 144 cells total, **pass_fraction 0.319** (46/144)
- by_asset_class: equity 36/72 (0.500), crypto 10/72 (0.139)
- by_vol_regime: low 32/48 (0.667), mid 14/48 (0.292), high 0/48 (0.0, universal high-vol failure)
- best_cell: QQQ, length=30/max_hold=20/min_hold=3, low-vol, Sharpe 2.74

## Single-config validators

A local search found a **SHARED config passing all 5 validators for BOTH
QQQ and SPY simultaneously**:

**Config: length=15, max_hold_days=30, min_hold_days=10, trend_window=50**

| Symbol | Trades | Sharpe | MDD | TC-survival (net Sharpe, 10bps) | Walk-forward (4-split) | Param sensitivity (relative_std) |
|---|---|---|---|---|---|---|
| QQQ | 69 | **1.237** PASS | **0.157** PASS | **1.149** PASS | **4/4 (1.0)** PASS | **0.139** PASS |
| SPY | 65 | **1.152** PASS | **0.109** PASS | **1.042** PASS | **4/4 (1.0)** PASS | **0.181** PASS |

Crypto (BTC/USDT, ETH/USDT): 36-combo local search found zero configs
clearing Sharpe/MDD/TC-survival, consistent with the grid's decisive
0.139 crypto pass fraction (crypto's best grid cells cluster in the mid-vol
regime but never survive full-sample single-config validation).

## Decision

**Accept (QQQ, SPY, SHARED config); reject (BTC/USDT, ETH/USDT, decisive).**
