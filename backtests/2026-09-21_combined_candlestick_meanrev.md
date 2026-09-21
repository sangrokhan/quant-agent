# Combined Multi-Pattern Bearish-Named Candlestick Mean-Reversion — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_combined_candlestick_meanrev.py`
**Source:** https://quantifiedstrategies.substack.com/p/candlestick-patterns-that-actually ("Candlestick Patterns That Actually Work: Ranked by Backtested Performance")

## Hypothesis

QuantifiedStrategies.com's systematic 75-pattern SPY backtest (1993-2026)
found several "bearish"-named candlestick patterns (Bearish Engulfing #1,
Three Outside Down #2, Dark Cloud Cover #3) plus bullish-reversal patterns
(Bullish Piercing Line #4, Three Inside Up #5) actually work as BULLISH
mean-reversion signals in equities. The source's headline result (net
profit 1,320%, win rate 74%, CAGR 8.3%, MDD 13%) came from COMBINING these
top-5 patterns into one OR-gated entry with a modified exit (close above
prior day's high, not a fixed hold). Individual patterns already tested in
this repo standalone and rejected; this iteration tests the COMBINED
OR-gate + modified-exit construction specifically (novel technique, 0 prior
"combined candlestick" KB hits).

## Grid test (Step 6)

`param_grid={"max_hold_days": [5, 10, 15, 20]}`, symbols
`{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.25 (12/48 cells)**
- By asset class: equity 12/24 (0.50), crypto 0/24 (0.00 -- decisive crypto reject)
- By vol regime: low 4/16, mid 4/16, high 4/16 (uniform, unlike most prior
  strategies -- edge is NOT confined to one vol regime, a positive sign)
- Best avg-Sharpe config: SPY, max_hold_days=5 (avg cell Sharpe 1.064)
- Worst cell: BTC/USDT, max_hold_days=5, low-vol regime, Sharpe -1.27

## Single-config validation (Step 7)

Config: `max_hold_days=5` for both QQQ and SPY.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe after 10bps/trade) |
|---|---|---|---|
| QQQ | 0.678 (FAIL, thr 1.0) | 0.168 (PASS, thr 0.25) | 0.275 (FAIL, thr 0.5) |
| SPY | **1.052 (PASS)** | **0.123 (PASS)** | 0.455 (FAIL, thr 0.5, near-miss) |

`walk_forward` validator hit a pre-existing repo bug
(`vectorbt.utils.splitting` `AttributeError` -- same issue as this cron
trigger's iteration 1) unrelated to this strategy; not completed.

## Decision: **REJECT (SPY near-miss)**

QQQ decisively fails Sharpe (0.678 < 1.0). SPY passes Sharpe (1.052) and MDD
(0.123) but narrowly fails transaction-cost-survival (0.455 vs 0.5
threshold) due to high turnover (250 trades over the sample, short
max_hold_days=5 combined with OR-gated multi-pattern entries generates
frequent round-trips). This is a genuine near-miss worth revisiting with a
min_hold_days-style turnover-reduction gate (same rescue pattern already
validated in this repo for the XLP range-band strategy, 2026-09-21-266) in
a future iteration. Grid shows the edge is NOT confined to one volatility
regime (uniform 4/16 pass across low/mid/high), a more encouraging breadth
signal than most rejected strategies in this KB, but crypto is a decisive
0/24 reject across all cells -- candlestick reversal patterns tuned on
mean-reverting equity index behavior do not transfer to crypto.
