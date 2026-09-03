# Backtest Report: Elder Impulse System (Long-Only, Impulse-Reversal Exit)

**Strategy file:** `strategies/2026-09-04_elder_impulse_system.py`
**Knowledge base id:** 2026-09-04-064

## Hypothesis

Per Alexander Elder's Impulse System (Google AI-overview synthesis): a
13-period EMA and MACD Histogram (12/26/9) jointly classify each bar as
green (both rising = bullish impulse), red (both falling = bearish
impulse), or blue (mixed/neutral). Long entry on close of a green bar;
exit immediately when the bar changes away from green (impulse-reversal
exit, simpler of two documented exits).

Source: Google AI-overview synthesis (web_search failed with a
DDGS/Yahoo TLS connection error, fell back to browser_exec).

## Grid test summary

- Grid: `ema_window` in {9,13,20} x symbols {QQQ,SPY,BTC/USDT,ETH/USDT}
  x 3 vol-regime terciles = 36 cells.
- pass_fraction: 0.25 (9/36)
- by_asset_class: equity 9/18, crypto 0/18
- by_vol_regime: low 6/12, mid 3/12, high 0/12
- best_cell: SPY, ema_window=13, low-vol tercile, Sharpe 2.25 (narrow-slice artifact)
- worst_cell: QQQ, ema_window=13, high-vol tercile, Sharpe -0.28

## Full-sample sweep (ema_window in {9,13,20})

| Symbol | w=9 | w=13 | w=20 |
|---|---|---|---|
| QQQ | 0.522 | 0.609 | 0.730 |
| SPY | 0.626 | 0.642 | **0.977** |

Primary config selected: `ema_window=13` (source's default parameter).

## Single-config validator suite (primary config, ema_window=13)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio | 0.609 (fail, thr 1.0) | 0.642 (fail, thr 1.0) |
| Max drawdown | 0.251 (fail, thr 0.25, borderline) | 0.214 (pass) |
| TC survival | 0.212 (fail, thr 0.5) | 0.127 (fail, thr 0.5) |
| Walk-forward | 3/4 splits positive (pass) | 3/4 splits positive (pass) |
| Parameter sensitivity | rel.std 0.137 (pass) | rel.std 0.216 (pass) |

## Outcome

**Rejected.** Full-sample Sharpe is decisively below threshold on both
QQQ (0.609) and SPY (0.642) at the source's default ema_window=13 (though
SPY improves to 0.977, still a near-miss, at ema_window=20). Extremely
high trade frequency (248 completed round-trips over 7.7yr on both
symbols, roughly one every 8 trading days) drives outsized transaction
cost drag (net-of-cost Sharpe collapses to 0.21/0.13). Crypto rejected
decisively (0/18 grid cells).

## Notes

Novelty: first Elder Impulse System (dual-condition color-coded bar
classifier requiring BOTH a moving-average slope AND an oscillator-slope
condition simultaneously) strategy tested in this repo — distinct from
every prior single-indicator crossover/threshold strategy. The
impulse-reversal exit (exit on ANY loss of the green-bar condition,
i.e. either EMA or MACD-hist slope flips) is likely the primary driver of
the high trade frequency and consequent transaction-cost failure; a
future loop could test the alternative documented exit (trailing stop
below the 13 EMA / prior 2-bar low) which would likely reduce turnover
substantially.
