# Backtest Report: EMA50 Pullback-Group Chandelier Breakeven Breakout

**Strategy file:** `strategies/2026-09-23_ema50_pullback_group_chandelier_breakeven.py`
**KB id:** 2026-09-23-148
**Outcome:** REJECTED (near-miss on Sharpe)

## Hypothesis + Source

Per MGEQuant's Sept 18 2026 dev log
(https://mgequant.com/DevelopmentLogs/Strategies/2026/09-September.html, read
via `browser_exec` — `web_search` only surfaced generic backend listing
pages for TASC-style queries this iteration): after an EMA(50) uptrend
cross, wait for a run of pullback bars, place a stop-entry beyond the
extreme of that pullback group, target 2R, move stop to breakeven at 1R,
then trail with a Chandelier Exit.

## Single-config validators (QQQ, full sample 2018-01-01 to 2026-09-01)

Config: `pullback_min_bars=2, breakout_atr_mult=0.5, chandelier_mult=2.5`
(grid-best cell config)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.828 | 1.0 |
| Max drawdown | pass | 0.162 | 0.25 |
| Transaction cost survival | pass | 0.658 | 0.5 |
| Walk-forward (4 splits) | pass | 1.0 (4/4) | 0.75 |
| Parameter sensitivity | pass | 0.187 rel-std | 0.5 |

4/5 validators pass cleanly; Sharpe is the sole failure, and it's a
near-miss (0.83 vs 1.0), not decisive.

## Grid test summary

216 cells: `pullback_min_bars ∈ {2,3,4}` × `breakout_atr_mult ∈ {0.1,0.25,0.5}`
× `chandelier_mult ∈ {2.5,3.0}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` ×
3 vol-regime terciles.

- **pass_fraction:** 0.245 (53/216)
- **By asset class:** equity 37/108 (34%), crypto 16/108 (15%)
- **By vol regime:** low 48/72 (67%), mid 2/72 (3%), high 3/72 (4%)
- **Best cell:** QQQ, low-vol regime, `pullback_min_bars=2/breakout_atr_mult=0.5/chandelier_mult=2.5`, Sharpe 2.57
- **Worst cell:** SPY, mid-vol regime, Sharpe -1.11

The edge is real but heavily concentrated in low-volatility regimes — the
full-sample Sharpe of 0.83 is diluted by mid/high-vol regime cells that
decisively fail. A future iteration could gate entries to a cheap low-vol
regime proxy (analogous to the accepted 2026-09-03-001 BB mean-reversion
vol-regime gate) to try to isolate and preserve the working slice.

## Decision

**Rejected.** Sharpe threshold not met on full sample despite otherwise
clean validators. Strategy/report kept as a documented near-miss for a
future vol-regime-gated rescue attempt.
