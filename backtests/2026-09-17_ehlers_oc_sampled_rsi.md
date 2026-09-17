# Backtest Report: Ehlers OC-Sampled RSI Oversold-Recovery

**Strategy file:** `strategies/2026-09-17_ehlers_oc_sampled_rsi.py`
**Hypothesis id:** 2026-09-17-167

## Source

TASC (Technical Analysis of Stocks & Commodities) March 2023, John F.
Ehlers, "Every Little Bit Helps", via
https://traders.com/Documentation/FEEDbk_docs/2023/03/TradersTips.html
(visited this iteration, see knowledge_base/visited_pages.jsonl).

Ehlers' proposal: sample price as `(Open+Close)/2` instead of raw `Close`
before feeding it into a downstream indicator (his own demo: RSI(14)) to
reduce noise. First "OC-sampled input" strategy in this repo -- a data
SAMPLING technique, not a new oscillator formula, applied here to a
standard Wilder RSI(14) oversold-recovery crossover.

## Trading rule

RSI computed on `(Open+Close)/2` crossing up through `oversold` = long
entry, gated by `close > SMA(trend_window)`; exit on crossing back down
through `overbought` or a `max_hold_days` time-stop.

## Step 6 grid summary (rsi_period x oversold x max_hold_days, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-2026)

- 324 cells total, **pass_fraction 0.133** (43/324)
- by_asset_class: equity 32/162 (0.198), crypto 11/162 (0.068)
- by_vol_regime: low 26/108 (0.241), mid 7/108 (0.065), high 10/108 (0.093)
- best_cell: QQQ, rsi_period=14/oversold=35/max_hold=20, low-vol, Sharpe 2.27

## Single-config validators

A wider local search (5-dim: rsi_period x oversold x overbought x
max_hold_days x trend_window, 324 combos per symbol) found:

**SPY: rsi_period=10, oversold=40, overbought=70, max_hold_days=30, trend_window=150**

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Trades | 26 | -- | -- |
| Sharpe | 1.433 | 1.0 | PASS |
| Max drawdown | 0.104 | 0.25 | PASS |
| TC-survival (net Sharpe, 10bps) | 1.373 | 0.5 | PASS |
| Walk-forward (4-split) | 1.0 (4/4) | 0.75 | PASS |
| Parameter sensitivity (relative_std) | 0.473 | 0.5 | PASS (borderline) |

**QQQ:** best config found (`rsi_period=7, oversold=45, overbought=75,
max_hold_days=20, trend_window=100`) reaches Sharpe 0.905 -- a near-miss
that never clears 1.0 across a 192-combo local search around the grid's
promising region. Rejected.

Crypto (BTC/USDT, ETH/USDT): 27-combo local search found zero configs
clearing Sharpe/MDD/TC-survival, consistent with the grid's 0.068 crypto
pass fraction. Decisive rejection.

## Decision

**Accept (SPY only, per above config); reject (QQQ near-miss, crypto decisive).**
