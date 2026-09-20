# Backtest Report: Price MACD Crossover Gated by OBV-MACD Confirmation

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_macd_obv_confirmation.py`
**Source:** https://statoasis.com/overfit/research/obv-macd-vs-traditional-macd-which-one-wins (Ali Casey / StatOasis, visited via `browser_exec`)

## Hypothesis

Per StatOasis's 9,216-backtest study: replacing the traditional price MACD
with an OBV-based MACD loses more often than it wins, but using OBV-MACD
as a CONFIRMATION filter layered on the traditional price MACD entry
(long only when price MACD crosses up AND OBV-MACD histogram already
agrees) wins decisively in the source's own large-scale sweep (better
profit factor in 67.3% of matched pairs, smaller drawdowns in 85.7%).

## Grid Test Summary (Step 6)

`param_grid={"signal_len": [5,9,14], "max_hold_days": [20,40,60]}`,
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Total cells:** 108, **passed:** 28, **pass_fraction:** 0.259
- **By asset class:** equity 22/54 (0.407), crypto 6/54 (0.111)
- **By vol regime:** low 19/36 (0.528), mid 3/36 (0.083), high 6/36 (0.167)
- **Best cell:** crypto/ETH/USDT, low-vol, `signal_len=9, max_hold_days=20`,
  Sharpe 2.21
- Best full-sample-averaged equity config: `signal_len=9, max_hold_days=40`
  (avg equity Sharpe 0.914)

## Single-Config Validation (Step 7) — `signal_len=9, max_hold_days=40`

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd (4-split) | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.790 (FAIL, thr 1.0) | 0.186 (PASS) | 0.703 (PASS) | 1.00 (PASS) | 0.171 (PASS) |
| SPY | 0.783 (FAIL, thr 1.0) | 0.096 (PASS) | 0.649 (PASS) | 1.00 (PASS) | 0.165 (PASS) |
| BTC/USDT | 0.362 (FAIL) | 0.648 (FAIL, decisive) | 0.340 (FAIL) | 0.75 (PASS) | 0.373 (PASS) |

## Decision (Step 8): **REJECTED**

Full-period Sharpe (0.78-0.79 on both QQQ and SPY) falls short of the 1.0
threshold, despite passing every other validator cleanly (MDD, tx-cost,
walk-forward, parameter sensitivity all pass with good margin -- the
lowest parameter-sensitivity relative std of any strategy tested this
cron trigger, 0.165-0.171, meaning this construction is genuinely robust
across the signal_len/max_hold_days grid, just not quite profitable
enough at full-sample). BTC/USDT is a decisive reject with a severe
drawdown (0.648). This is an honest near-miss on equity worth flagging: the
grid's low-vol pass rate (0.528) suggests the same low-vol-regime-gating
approach that has rescued other near-misses in this repo (e.g. the
accepted BB mean-reversion strategy) could plausibly push this over
threshold in a future iteration.
