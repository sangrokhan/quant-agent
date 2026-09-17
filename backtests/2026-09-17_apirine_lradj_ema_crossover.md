# Backtest Report: Apirine LRAdj EMA vs EMA Crossover

**Strategy file:** `strategies/2026-09-17_apirine_lradj_ema_crossover.py`
**Hypothesis id:** 2026-09-17-165

## Source

TASC (Technical Analysis of Stocks & Commodities) September 2022 Traders'
Tips (implementing the August 2022 article), Vitali Apirine, "The Linear
Regression-Adjusted Exponential Moving Average". Fully disclosed
TradeStation EasyLanguage series function read via browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2022/09/TradersTips.html
(this iteration used browser_exec Google search to discover the month, then
browser_exec page-read for the formula -- web_search backend intermittently
500s, this query succeeded via web_search but the page read used
browser_exec as per this repo's established navigate-and-extract pattern).

LRAdj EMA's adaptive component measures normalized distance of price from
its own rolling linear-regression trendline -- a DISTINCT adaptive-rate
mechanism from every other adaptive-EMA family already in this repo (RS EMA
= up/down-day asymmetry, id 2026-09-17-164 this same trigger; Relative VIX
Strength EMA = VIX asymmetry, rejected 2026-09-12-184; TRAdj EMA = True
Range, ids 2026-09-12-196/197).

## Trading rule

LRAdj EMA crossing above a plain EMA of the same `periods` length (source's
own suggested crossover pairing) = long entry; exit on reverse cross (with
`min_hold_days` hysteresis) or `max_hold_days` time-stop.

## Step 6 grid summary (periods x mltp x max_hold_days, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-2026)

- 216 cells total, **pass_fraction 0.269** (58/216)
- by_asset_class: equity 54/108 (0.500), crypto 4/108 (0.037)
- by_vol_regime: low 40/72 (0.556), mid 18/72 (0.25), high 0/72 (0.0) --
  universal failure in high-vol regime
- best_cell: SPY, periods=30/mltp=3/max_hold=20, low-vol, Sharpe 2.86
- worst_cell: QQQ, periods=50/mltp=3/max_hold=40, high-vol, Sharpe -0.75

## Single-config validators

A local parameter search around the grid's promising region found a
**SHARED config that passes all 5 validators for BOTH QQQ and SPY
simultaneously** (no per-symbol retune needed):

**Config: periods=30, pds=30, mltp=4, max_hold_days=20, min_hold_days=3**

| Symbol | Trades | Sharpe | MDD | TC-survival (net Sharpe, 10bps) | Walk-forward (4-split) | Param sensitivity (relative_std) |
|---|---|---|---|---|---|---|
| QQQ | 84 | **1.067** PASS | **0.208** PASS | **0.960** PASS | **4/4 (1.0)** PASS | **0.125** PASS |
| SPY | 87 | **1.250** PASS | **0.151** PASS | **1.097** PASS | **4/4 (1.0)** PASS | **0.131** PASS |

Crypto (BTC/USDT, ETH/USDT): local search of 48 configs x 2 symbols found
**zero** configs clearing all three of Sharpe/MDD/TC-survival, consistent
with the grid's decisive 0.037 crypto pass fraction.

## Decision

**Accept (QQQ, SPY, SHARED config); reject (BTC/USDT, ETH/USDT, decisive).**
