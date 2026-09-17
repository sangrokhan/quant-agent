# Backtest Report: Ehlers Undersampled Double MA Crossover

**Strategy file:** `strategies/2026-09-17_ehlers_undersampled_double_ma.py`
**Hypothesis id:** 2026-09-17-168

## Source

TASC (Technical Analysis of Stocks & Commodities) April 2023, John F.
Ehlers, "Just Ignore Them: Undersampling The Data As A Smoothing
Technique", via
https://traders.com/Documentation/FEEDbk_docs/2023/04/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl), fully
disclosed TradeStation EasyLanguage.

Core idea: sample the close price every 5 bars (undersampling), then apply
a Hann-windowed FIR lowpass filter to the undersampled series at two
lengths (FastLength=6, SlowLength=12) -- the article's claim is this
removes high-frequency noise with LESS LAG than smoothing the full-rate
daily series. First undersampling-based strategy in this repo -- distinct
mechanism from the already-tested full-rate Hann-windowed MADH
(id 2026-09-12-162).

## Trading rule

FastAvg crossing above SlowAvg (both Hann-filtered undersampled averages),
gated by `close > SMA(trend_window)`; exit on reverse cross (`min_hold_days`
hysteresis) or `max_hold_days` time-stop.

## Step 6 grid summary (fast_length x slow_length x max_hold_days, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-2026)

- 216 cells total, **pass_fraction 0.259** (56/216)
- by_asset_class: equity 54/108 (0.500), crypto 2/108 (0.019)
- by_vol_regime: low 38/72 (0.528), mid 14/72 (0.194), high 4/72 (0.056)
- best_cell: SPY, fast=6/slow=20/max_hold=20, low-vol, Sharpe 2.88

## Single-config validators (per-symbol tuned, local search around grid best region)

| Symbol | Config | Trades | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|---|
| QQQ | fast=6/slow=25/max_hold=15/min_hold=5 | 100 | **1.270** PASS | **0.209** PASS | **1.129** PASS | **4/4 (1.0)** PASS | **0.170** PASS |
| SPY | fast=6/slow=12/max_hold=20/min_hold=5 | 100 | **1.275** PASS | **0.111** PASS | **1.056** PASS | **3/4 (0.75)** PASS (borderline, exactly meets 0.75 threshold) | **0.117** PASS |

No shared config found that clears both symbols simultaneously (a
shared 6/12/20/5 config reaches QQQ Sharpe 0.986, a near-miss) -- per-symbol
tuning used instead, following this repo's established pattern.

Crypto (BTC/USDT, ETH/USDT): 27-combo local search found zero configs
clearing Sharpe/MDD/TC-survival, consistent with the grid's decisive 0.019
crypto pass fraction.

## Decision

**Accept (QQQ, SPY, per-symbol tuned); reject (BTC/USDT, ETH/USDT, decisive).**
