# TRIX Signal-Line Crossover (zero-line filtered) — Backtest Report

**Hypothesis** (kb id 2026-09-04-038): TRIX (rate-of-change of a
triple-smoothed EMA of closing prices, standard 15-period) crossing above
its 9-period-EMA signal line, filtered to only trade when TRIX > 0, signals
a long entry that benefits from the triple smoothing's noise-filtering
compared to simpler oscillators.

**Source**: Google AI-overview + multiple TA sites (TradeTaurex,
LightningChart, WarriorTrading) — web_search failed with a DDGS/Yahoo TLS
connection error this iteration, fell back to browser_exec.

## Grid test (Step 6)

`param_grid = {trix_window: [10,15,20], signal_window: [9]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3,
2019-01-01 to 2026-09-01. 36 total cells.

- pass_fraction: **0.056** (2/36) — one of the lowest pass fractions in this log
- by_asset_class: equity 2/18, crypto 0/18
- by_vol_regime: low 2/12, mid 0/12, high 0/12
- best_cell: SPY, trix_window=20, signal_window=9, low-vol tercile, Sharpe 1.864 (not representative of full sample, see below)

## Full-sample validators (Step 7) — grid-best config (trix_window=20, signal_window=9)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Trades |
|---|---|---|---|---|
| QQQ | -0.096 (fail, thr 1.0) | 0.250 (borderline pass, thr 0.25) | -0.146 (fail, thr 0.5) | 26 |
| SPY | 0.032 (fail, thr 1.0) | 0.132 (pass) | -0.034 (fail) | 24 |

## Decision: REJECTED (all asset classes)

Full-sample Sharpe is essentially zero-to-negative on both QQQ (-0.096) and
SPY (0.032) — a decisive, unambiguous failure, not a near-miss. Net-of-cost
Sharpe goes negative on both. The grid's low-vol-tercile "best cell" (Sharpe
1.864) was entirely non-representative of full-sample performance. Walk-
forward and parameter sensitivity skipped per Step 7 minimum-subset
guidance (Sharpe already fails decisively). Crypto rejected decisively
(0/18 grid cells). This is one of the clearest rejections in the log —
combining a signal-line crossover with a zero-line filter did not produce
even a marginally viable equity strategy on this sample.
