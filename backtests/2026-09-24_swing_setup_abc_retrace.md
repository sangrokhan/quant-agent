# Bulkowski Swing Trading Setup (A-B-C Retrace) — Backtest Report

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_swing_setup_abc_retrace.py`
**Source:** https://thepatternsite.com/SwingSetup.html (Thomas Bulkowski),
read via browser_exec.

## Hypothesis

Identify a confirmed 5-day swing low (A), the following confirmed swing high
(B), and the subsequent confirmed swing low (C) — a rise A->B followed by a
retrace B->C. Buy at C (approximated here as the next bar's close-basis
entry). Exit when price closes at/above the target (highest CLOSE from A to
C) or falls `stop_pct` (5% default, per source) below entry, whichever comes
first. Source's own updated (3/26/2020) 489-stock 2009-2020 bull-market test
found Fibonacci retracement depths (38/50/62%) are NOT statistically more
common than any other depth, so unlike the repo's existing Fibonacci-band
strategy (2026-09-03-022) this strategy does not gate on retracement depth
at all — it trades every confirmed A-B-C swing.

## Grid test summary (Step 6)

`swing_window` in {5,10}, `stop_pct` in {0.05,0.08}, equity {QQQ,SPY} +
crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 48 cells.

- **pass_fraction: 0.479** (23/48)
- **by_asset_class:** equity 19/24, crypto 4/24
- **by_vol_regime:** low 8/16, mid 8/16, high 7/16 (holds up reasonably
  evenly across vol regimes, unlike most mean-reversion strategies tested
  in this repo which concentrate almost entirely in low-vol)
- **best_cell:** swing_window=5, stop_pct=0.05, QQQ, low-vol, Sharpe 2.262
- **worst_cell:** swing_window=10, stop_pct=0.08, ETH/USDT, high-vol,
  Sharpe -0.579

## Single-config validation (Step 7)

Config: `swing_window=5, stop_pct=0.05` (grid's best cell). Full sample
2016-01-01 to 2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) | Trades |
|---|---|---|---|---|---|
| QQQ | 1.127 PASS | 0.284 **FAIL** | 1.043 PASS | 0.132 PASS | 59 |
| SPY | 1.111 PASS | **0.143 PASS** | 1.022 PASS | 0.208 PASS | 54 |
| BTC/USDT | 0.543 **FAIL** | 0.334 **FAIL** | 0.316 **FAIL** | 0.085 PASS | 1397 |
| ETH/USDT | 0.632 **FAIL** | 0.491 **FAIL** | 0.427 **FAIL** | 0.125 PASS | 1398 |

`check_walk_forward` errored with the pre-existing repo bug
(`vbt.utils.splitting` missing, consistent with all prior 2026-09-24
entries); skipped per `suggested_workload=max` note that this pre-existing
bug is out of scope to fix mid-loop.

Note: crypto trade counts (1397-1398 over 10.5 years, i.e. multiple trades
per week) are far higher than the equity trade counts (54-59, roughly one
every ~7 weeks) — the swing-detection is firing on much noisier
higher-frequency crypto price action, producing an overtraded, cost-eroded
result on crypto specifically (net Sharpe after 10bps costs collapses to
0.32-0.43 for crypto vs. staying >1.0 for equities).

## Decision

**Accepted for SPY only.** All 4 runnable validators pass for SPY (Sharpe
1.111, MDD 0.143, net-of-cost Sharpe 1.022, parameter sensitivity 0.208).
QQQ fails only max-drawdown (0.284 vs 0.25 threshold) — a near-miss worth
revisiting with a tighter stop or vol-regime gate in a future iteration.
Crypto (BTC/USDT, ETH/USDT) rejected decisively: fails Sharpe, MDD, and
net-of-cost Sharpe, driven by excessive trade frequency on noisier crypto
price action eroding returns after transaction costs.
