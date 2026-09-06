# Backtest report: Turtle Trading System 2 (55-day breakout, 2N stop)

**Strategy file:** `strategies/2026-09-07_turtle_system2_atr_stop.py`
**Outcome:** ACCEPTED (QQQ only) — all validators pass on QQQ; SPY fails Sharpe; crypto rejected decisively.

## Hypothesis

Per https://www.theturtletrader.com/turtle-trading-rules: System 2 is the
Turtles' longer-term companion to System 1 (already tested and accepted in
this repo, id=2026-09-06-125). Entry: buy at close on a new 55-day high,
with EVERY signal taken (unlike System 1's "skip after a winning breakout"
filter — "Every signal is taken, no filter"). Exit: close makes a new
20-day low (System 2's own opposite-extreme exit, longer than System 1's
10-day) or a 2N ATR protective stop, whichever comes first. N = 20-day
average true range, same construction as System 1.

## Grid test summary (Step 6)

`param_grid={"entry_window": [40,55,70], "stop_atr_mult": [1.5,2.0,2.5]}`,
`symbols={"equity": [QQQ, SPY], "crypto": [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, period 2019-01-01 to 2026-09-01 (108 cells).

- **pass_fraction: 0.194** (21/108 cells) — highest of the four strategies tested this cron run
- **by_asset_class:** equity 21/54 passed; crypto **0/54** (decisive reject)
- **by_vol_regime:** low 18/36; mid 3/36; high 0/36 — same low-vol-regime concentration pattern seen in several prior strategies this run, but this time the full-sample QQQ check still clears the bar (see below)
- **best_cell:** entry_window=55, stop_atr_mult=2.5, SPY, low-vol, Sharpe 2.88

## Single-config validation (Step 7) — best grid config (entry_window=55, stop_atr_mult=2.5), full sample

| Symbol | Sharpe (thr 1.0) | Max DD (thr 0.25) |
|---|---|---|
| QQQ | **1.025 PASS** | 0.145 PASS |
| SPY | 0.474 FAIL | 0.225 PASS |

Full validator suite on QQQ:
- Sharpe: 1.025 PASS (thr 1.0) — a narrow pass, worth flagging as borderline
- Max drawdown: 0.145 PASS (thr 0.25)
- Transaction cost survival (10bps/trade, 36 trades): net Sharpe 0.975 PASS (thr 0.5)
- Walk-forward (manual 4-slice split, `vbt.utils.splitting` API bug workaround): splits Sharpe [1.16, -0.16, 1.87, 0.77] → 3/4 positive → pass_fraction 0.75 PASS (thr 0.75)
- Parameter sensitivity (entry_window sweep at stop_atr_mult=2.5: {40: 1.059, 55: 1.025, 70: 0.907}): relative_std **0.065 PASS** (thr 0.5) — a genuinely robust plateau, unlike the OU strategy's fragile spike earlier this run; QQQ's edge holds up across a wide entry-window range, not just at the exact grid-best value.

## Conclusion

**Accepted for QQQ only.** Unlike this run's earlier low-vol-only rejects
(APZ, ADXR), Turtle System 2's full-sample Sharpe on QQQ clears 1.0 and the
parameter sensitivity is genuinely robust (0.065 relative std — the
strongest parameter-stability result of anything tested this run), giving
confidence this isn't an overfit low-vol-regime artifact even though the
grid breakdown shows a similar low-vol concentration pattern. SPY and crypto
do not clear the bar and should not be traded with this strategy — the
honest scope is QQQ (Nasdaq-100, higher-beta/higher-momentum universe) only,
consistent with several other momentum/trend-following strategies already
accepted QQQ-only in this repo (e.g. plain Donchian breakout 2026-09-04-054).
The QQQ Sharpe pass (1.025) is narrow, so a future loop revisiting this
strategy should treat it as a moderate- rather than high-confidence accept.
