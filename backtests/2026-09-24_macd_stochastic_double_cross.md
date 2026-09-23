# MACD + Stochastic Double Cross — Backtest Report (2026-09-24)

## Hypothesis

Long entry requires BOTH the MACD line crossing above its own signal line
AND Stochastic %K crossing above %D, with the two crossovers occurring
within `sync_window` bars of each other. Exit when EITHER indicator's
crossover reverses, or a `max_hold_days` time-stop.

Source: The Forex Geek, "MACD Stochastic Double Cross Strategy"
(https://theforexgeek.com/macd-stochastic-double-cross-strategy/). Distinct
from this repo's Schaff Trend Cycle family (6+ prior entries) — STC fuses
MACD and double-stochastic into ONE composite oscillator via a specific
recursive formula; this strategy keeps MACD and Stochastic as two SEPARATE
raw indicator lines and requires their independent crossovers to
synchronize in time, following the same synchronized-dual-confirmation
pattern validated earlier this cron trigger for PPO+TRIX (2026-09-24-023).

## Strategy file

`strategies/2026-09-24_macd_stochastic_double_cross.py`

## Grid test summary (Step 6)

72 cells: `sync_window ∈ {1, 2, 3} × max_hold_days ∈ {20, 40}` × symbols
`{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime terciles, 2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | **0.722 (52/72) — best of any strategy this cron trigger** |
| equity pass | **36/36 (perfect — every config × every vol regime)** |
| crypto pass | 16/36 (BTC/USDT perfect 6/6 at sync_window=1) |
| low-vol pass | 24/24 (perfect) |
| mid-vol pass | 14/24 |
| high-vol pass | 14/24 — unusually strong; most strategies this trigger score ~0 in high-vol |
| best cell | BTC/USDT low-vol, sync_window=1/max_hold=20, Sharpe 2.90 |
| worst cell | BTC/USDT mid-vol, sync_window=2/max_hold=20, Sharpe 1.06 (still positive!) |

## Single-config validation (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param-sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sync_window=2, max_hold=20 | 1.440 ✅ | 0.155 ✅ | 0.748 ✅ | 1.0 ✅ | 0.115 ✅ | **ACCEPT** |
| SPY | sync_window=2, max_hold=20 | 1.710 ✅ | 0.119 ✅ | 0.676 ✅ | 1.0 ✅ | 0.029 ✅ | **ACCEPT** |
| BTC/USDT | sync_window=1, max_hold=20 | 2.333 ✅ | 0.165 ✅ | 2.180 ✅ | 1.0 ✅ | 0.222 ✅ | **ACCEPT** |
| ETH/USDT | sync_window=1, max_hold=20, **leverage_cap=0.85** | 2.292 ✅ | 0.242 ✅ | 2.162 ✅ | 1.0 ✅ | ~0 ✅ | **ACCEPT** |

ETH/USDT initially failed only MDD (0.281 vs 0.25, a narrow near-miss
unlike most crypto MDD failures this trigger which were decisive) —
`leverage_cap=0.85` fixed it cleanly with Sharpe unchanged.

## Decision

**Accepted for the full 4-symbol universe: QQQ, SPY, BTC/USDT (full
exposure), ETH/USDT (leverage_cap=0.85).** All 5 validators pass on all 4
symbols with Sharpe ratios in the 1.4–2.3 range — the strongest single
strategy result (by both Sharpe magnitude and grid breadth) of this entire
cron trigger.
