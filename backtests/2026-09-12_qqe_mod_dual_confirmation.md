# QQE MOD (dual-QQE + Bollinger zero-line confirmation) — Backtest Report

**Hypothesis:** Two independent QQE (Qualitative Quantitative Estimation)
calculations at different sensitivities -- a fast one whose trend flip
drives the entry trigger, and a slow one (zero-centered) confirmed by its
own Bollinger Band "zero line" -- must AGREE before a long entry fires. Per
https://www.tradingview.com/script/TpUW4muw-QQE-MOD/ (Mihkel00, creator's own
page: "When both of them agree - you get a blue or a red bar") and
https://ataquant.com/trading-strategy-with-qqe-mod-indicator/ (worked
entry-rule confirmation). Distinct from the already-tested single-QQE
strategy (2026-09-08-162, rejected) which uses one QQE + a separate
EMA(100) trend filter, not a second independent QQE.

## Best config (from grid): bb_length=50, bb_mult=0.35, max_hold_days=15

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.368 (FAIL, thr 1.0) | 0.125 (pass) | 0.260 (FAIL, thr 0.5) | 0.50 (FAIL, thr 0.75) | 0.251 (pass) |
| SPY | 0.301 (FAIL, thr 1.0) | 0.064 (pass) | 0.215 (FAIL, thr 0.5) | 0.50 (FAIL, thr 0.75) | 0.360 (pass) |

## Grid summary (bb_length in {30,50} x bb_mult in {0.2,0.35,0.5} x
max_hold_days in {15,20}, symbols QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- total_cells=144, passed_cells=16, pass_fraction=0.111
- by_asset_class: equity 16/72 passed, crypto 0/72 passed (decisive crypto reject)
- by_vol_regime: low 6/48, mid 8/48, high 2/48 (more evenly spread across
  regimes than the earlier Fisher-on-RSI entry this cron trigger, but still
  low overall pass rate)
- best_cell: bb_length=50/bb_mult=0.35/max_hold_days=15, QQQ, mid-vol,
  Sharpe=1.62

## Verdict: REJECTED

Full-sample Sharpe, TC-survival, and walk-forward all fail on both QQQ and
SPY at the grid's best config. Trade count is low (36 QQQ / 23 SPY over
~8.5 years), so the grid's occasional high-Sharpe cells are likely small-
sample noise rather than a durable edge. Crypto decisively rejected
(0/72). Not accepted; strategy file kept as a record of a tested/rejected
construction (dual-QQE + BB confirmation) for future novelty checks.
