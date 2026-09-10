# 2026-09-10 — Wilder RSI Failure Swing Bottom (REJECTED, sparse-signal near-miss)

## Hypothesis

Per https://fortunetalkstrading.blogspot.com/2022/03/rsi-failure-swing-strategy-explained.html
(J. Welles Wilder's classic RSI Failure Swing): the bullish "Failure Swing
Bottom" requires (1) an RSI swing low below the oversold level (30), (2) a
subsequent RSI swing high (the "fail point"), (3) a subsequent RSI swing low
that is higher than the first low AND stays out of oversold territory, then
(4) a buy trigger when RSI breaks back above the fail-point value. A
trend-reversal counter-trend entry, per the source. First RSI Failure Swing
strategy in this repo (distinct from plain oversold-threshold crosses and
raw price/RSI divergence, which lack the specific swing-break confirmation
structure).

Strategy file: `strategies/2026-09-10_rsi_failure_swing_bottom.py`

## Grid summary (swing_window in [2,3,5] x oversold_level in [25,30], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- 8/72 cells passed (pass_fraction 0.111), all 8 on equity — crypto 0/36 decisively.
- By vol regime: low 4/24, mid 4/24, high 0/24.
- Best cell: QQQ, swing_window=3, oversold_level=30, mid-vol tercile, Sharpe 1.85.
- Worst cell: SPY, swing_window=2, oversold_level=25, low-vol tercile, Sharpe -0.25.

## Full-sample quick check (swing_window=3, oversold_level=30, 2017-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Num trades |
|---|---|---|---|---|
| QQQ | 0.827 (FAIL, thr 1.0) | 0.117 (pass) | 0.802 (pass) | 12 |
| SPY | 0.279 (FAIL) | 0.123 (pass) | 0.246 (FAIL) | 12 |

## Decision: REJECT

QQQ fails Sharpe on the full sample (0.827 vs 1.0), and critically only 12
trades fire over the ~10-year sample — this is a structurally rare-signal
pattern (Wilder's own Failure Swing requires a specific 4-step RSI
swing-point sequence to align), making even the grid's best-cell Sharpe
(1.85) statistically fragile rather than a robust repeatable edge. Full
validator suite (walk-forward, parameter sensitivity) skipped as
unnecessary given the already-decisive full-sample Sharpe shortfall
combined with the sparse trade count that would make walk-forward splits
nearly signal-free. SPY decisively fails all three quick-check validators.
Crypto rejected decisively across the whole grid (0/36 cells).
