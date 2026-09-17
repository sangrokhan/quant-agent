# Backtest Report: Apirine Stochastic Distance Oscillator (SDO)

**Strategy file:** `strategies/2026-09-17_apirine_sdo_oversold_recovery.py`
**Hypothesis id:** 2026-09-17-170

## Source

TASC (Technical Analysis of Stocks & Commodities) June 2023, Vitali
Apirine, "The Stochastic Distance Oscillator", via
https://traders.com/Documentation/FEEDbk_docs/2023/06/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl), fully
disclosed TradeStation EasyLanguage.

SDO normalizes the magnitude of an N-bar price move against its own
trailing 200-bar min/max distance range, signs it by move direction, and
EMA-smooths. Distinct from classic Stochastic (normalizes close vs
high/low range) and every other Apirine oscillator already tested in this
repo (ROCWB, STMACD, HHLLS).

## Trading rule

Long when SDO crosses up through `oversold`, gated by `close >
SMA(trend_window)`; exit on crossing back down through `overbought` or a
`max_hold_days` time-stop.

## Step 6 grid summary (oversold x overbought x max_hold_days, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-2026)

- 324 cells total, **pass_fraction 0.127** (41/324)
- by_asset_class: equity 28/162 (0.173), crypto 13/162 (0.080)
- by_vol_regime: low 20/108 (0.185), mid 9/108 (0.083), high 12/108 (0.111)
- Source's own default thresholds (+40/-40) produced too few trades (7 over
  8.7yr QQQ) -- a wider local search of narrower thresholds (+-5 to +-20)
  found viable configs.

## Single-config validators (per-symbol tuned)

| Symbol | Config | Trades | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|---|
| QQQ | oversold=-15/overbought=20/max_hold=20/trend=150 | 22 | **1.182** PASS | **0.102** PASS | **1.132** PASS | **4/4 (1.0)** PASS | **0.144** PASS |
| SPY | oversold=-15/overbought=5/max_hold=20/trend=150 | 25 | **1.242** PASS | **0.057** PASS | **1.168** PASS | **4/4 (1.0)** PASS | **0.171** PASS |

Crypto (BTC/USDT, ETH/USDT): 36-combo local search found zero configs
clearing Sharpe/MDD/TC-survival, consistent with the grid's decisive 0.080
crypto pass fraction.

## Decision

**Accept (QQQ, SPY, per-symbol tuned); reject (BTC/USDT, ETH/USDT, decisive).**
