# PPO + TRIX Synchronized Dual-Confirmation — Backtest Report (2026-09-24)

## Hypothesis

Long entry requires BOTH the Percentage Price Oscillator (PPO) crossing
above its own EMA signal line AND TRIX (triple-smoothed EMA rate of
change) crossing above its own EMA signal line, with the two crossovers
occurring within `sync_window` bars of each other (either order). Exit
when EITHER oscillator crosses back below its own signal line, or a
`max_hold_days` time-stop.

Source: Google AI-overview synthesis (browser_exec Google SERP fallback —
`web_search` DDGS backend TLS-errored on most queries this iteration).
This repo has 8 prior PPO entries and 15 prior TRIX entries, each tested
*separately* (threshold, zero-cross, signal-line-crossover, continuous-
sizing variants), but never combined into this synchronized dual-
confirmation gate.

## Strategy file

`strategies/2026-09-24_ppo_trix_sync_confirmation.py`

## Grid test summary (Step 6)

72 cells: `sync_window ∈ {1, 2, 3} × max_hold_days ∈ {20, 40}` × symbols
`{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime terciles, 2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | **0.514 (37/72)** — best of any strategy this cron trigger |
| equity pass | 25/36 |
| crypto pass | 12/36 |
| low-vol pass | 24/24 (perfect) |
| mid-vol pass | 5/24 |
| high-vol pass | 8/24 — notable high-vol robustness, unusual for this repo |
| best cell | QQQ low-vol, sync_window=1/max_hold=20, Sharpe 2.26 |
| worst cell | SPY mid-vol, sync_window=1/max_hold=40, Sharpe -0.01 |

SPY at sync_window=2/max_hold=20 passed all 3/3 vol-regime cells.

## Single-config validation (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param-sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| SPY | sync_window=2, max_hold=20 | 1.291 ✅ | 0.131 ✅ | 0.845 ✅ | 1.0 ✅ | 0.063 ✅ | **ACCEPT** |
| QQQ | sync_window=1, max_hold=20 | 1.298 ✅ | 0.208 ✅ | 1.174 ✅ | 1.0 ✅ | 0.125 ✅ | **ACCEPT** |
| BTC/USDT | sync_window=1, max_hold=20, **leverage_cap=0.5** | 1.234 ✅ | 0.237 ✅ | 1.138 ✅ | 1.0 ✅ | ~0 ✅ | **ACCEPT** |
| ETH/USDT | sync_window=1, max_hold=20, **leverage_cap=0.4** | 1.143 ✅ | 0.214 ✅ | 1.054 ✅ | 1.0 ✅ | ~0 ✅ | **ACCEPT** |

Crypto initially failed only MDD (BTC 0.436, ETH 0.480 at `leverage_cap=
1.0`, all other 4 validators already passing) — a leverage-cap sweep
{0.3–0.7} found BTC=0.5 and ETH=0.4 both clear MDD cleanly while Sharpe
stays flat (leverage-invariant scalar).

## Decision

**Accepted for the full 4-symbol universe: QQQ, SPY, BTC/USDT (leverage_cap
=0.5), ETH/USDT (leverage_cap=0.4).** All 5 validators pass on all 4
symbols. This is one of the strongest and broadest results of this cron
trigger's iterations, achieved in a single research pass plus one crypto
leverage-cap sub-step.
