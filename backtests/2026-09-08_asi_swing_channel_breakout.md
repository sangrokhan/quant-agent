# Backtest Report: ASI Swing-Channel Breakout (2026-09-08_asi_swing_channel_breakout.py)

**Hypothesis / source:** https://gocharting.com/blog/accumulative-swing-index-trend-confirmation-strategy
(full page Access-Denied on fetch; rule taken verbatim from the Google
search-result snippet): "Enter long when ASI breaks above a prior swing
high, confirming trend continuation. Exit when ASI breaks below a prior
swing low." Operationalized as a Donchian-channel breakout applied directly
to Wilder's Accumulative Swing Index (ASI) line itself (reusing the same
Swing Index formula as strategies/2026-09-06_asi_zeroline_cross.py),
instead of that already-rejected zero-line-cross rule.

## Grid test summary (channel_window=[10,20,30] x max_hold_days=[15,20],
## limit_move=3.0, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026-09)

- Total cells: 72, passed: 16, pass_fraction = 0.222
- By asset class: equity 16/36, crypto 0/36 (decisive fail)
- By vol regime: low 12/24, mid 4/24, high 0/24
- Best cell: SPY, channel_window=30/max_hold_days=20, low-vol, Sharpe 2.809
- Worst cell: QQQ, channel_window=30/max_hold_days=20, high-vol, Sharpe -0.645

## Single-config validators (best config: channel_window=30,
## max_hold_days=20, limit_move=3.0), full sample 2019-2026-09

| Metric | SPY | QQQ | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe | 0.734 | 0.949 | >= 1.0 | FAIL (both, narrow miss) |
| Max Drawdown | 15.5% | 23.4% | <= 25% | PASS (both) |
| TC-survival net Sharpe (10bps, 52 trades) | 0.635 | 0.869 | >= 0.5 | PASS (both) |
| Walk-forward (manual 4-split, sub-Sharpe>0) | 4/4 (100%) | 3/4 (75%) | >= 75% | PASS (both) |

## Verdict: REJECTED (near-miss)

Three of four validators pass cleanly on both symbols, and the walk-forward
result is genuinely robust (4/4 and 3/4). Only full-sample Sharpe misses
the >=1.0 bar, and QQQ (0.949) misses by a hair. This is a much stronger
candidate than the typical rejected strategy in this repo -- worth
revisiting with a slightly wider channel_window or a volatility-scaled
position size to push Sharpe over 1.0, if a future iteration wants to
follow up. Crypto rejected decisively (0/36).
