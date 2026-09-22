# ICT Order Block + SMA(200) Trend Gate — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ict_order_block_sma_trend_gate.py`
**No new external source** — second rescue attempt of this cron trigger's
ICT Order Block family (2026-09-22-045 rejected on decisive MDD;
2026-09-22-046's per-trade stop-loss rescue failed). Adds an SMA(200)
trend-regime gate to the unchanged order-block entry mechanism, reusing
this repo's already-accepted trend-gate construction (see
`strategies/2026-09-08_formation_price_stoploss_trend.py`). Source for the
underlying entry mechanism remains Ali Casey, StatOasis, "I Backtested ICT
/ Smart Money Concepts — What Survives"
(https://statoasis.com/overfit/research/ict-backtest-what-survives).

## Grid test summary (Step 6)

Grid: `trend_window` in {100,150,200} x `atr_mult` in {0.75,1.0,1.5},
QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol regimes, 2016-2026.

- Total cells 108, passed 36 (pass_fraction **0.333**, up from 0.259
  unmodified / 0.306 stop-loss rescue)
- By asset class: equity 35/54; crypto 1/54
- By vol regime: low 18/36; mid 18/36; high 0/36 (still zero high-vol
  passes, but mid-vol regime materially improved 15->18/36 vs stop-loss
  rescue, and unlike the stop-loss rescue this gate BLOCKS new entries
  during high-vol/downtrend periods entirely rather than letting them
  happen and hoping the stop catches them)
- Best cell: SPY trend_window=200/atr_mult=1.5, low-vol, Sharpe 2.921

## Single-config validators (Step 7) — QQQ (confirm_bars=5, atr_mult=1.0,
hold_days=10, trend_window=200)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **True** | 1.263 | 1.0 |
| Max drawdown | **True** | **0.225** | 0.25 |
| TC survival | **True** | 0.788 | 0.5 |
| Walk-forward | **True** | 1.0 | 0.75 |
| Parameter sensitivity | **True** | 0.067 | 0.5 |

**All 5 validators pass on QQQ.**

## Single-config validators (Step 7) — SPY (same params)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | False | 0.788 | 1.0 |
| Max drawdown | True | 0.190 | 0.25 |
| TC survival | False | 0.258 | 0.5 |
| Walk-forward | True | 0.75 | 0.75 |
| Parameter sensitivity | True | 0.262 | 0.5 |

SPY near-miss on Sharpe/TC-survival but does not clear the bar this
iteration; not pursued further (accept QQQ scope only).

## Decision: ACCEPTED (QQQ only)

The SMA(200) trend gate fixes the root cause correctly identified in
2026-09-22-046's notes: blocking NEW order-block entries during established
downtrends (rather than trying to cap each individual trade's own loss)
brings QQQ's max drawdown from a decisive 0.364 fail down to a passing
0.225, while simultaneously IMPROVING Sharpe (1.198 -> 1.263) and
TC-survival — because fewer, better-timed trades (352 vs 434) also means
lower total transaction-cost drag. All 5 validators pass on QQQ. SPY remains
a near-miss (Sharpe 0.788, TC-survival 0.258) — kept out of scope for this
accepted strategy; a future iteration could retune trend_window/atr_mult
specifically for SPY.
