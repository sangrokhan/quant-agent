# TD Sequential (DeMark) TD Buy Setup 9-count exhaustion — Backtest Report

**Hypothesis** (kb id 2026-09-04-032): a "TD Buy Setup" completes when 9
consecutive daily closes each print lower than the close 4 bars prior,
signaling seller exhaustion; long-only entry on fresh completion, exit on
close crossing back above a short SMA or after `max_hold_days`.

**Source**: Google search snippets (web_search failed 5x with a DDGS/Yahoo
TLS error this iteration, fell back to browser_exec per RESEARCH_LOOP.md) —
discoveryalert.com.au's sequential-nine-exhaustion article and a Sofien
Kaabar Medium piece, both surfaced in snippet form; detail pages 404'd on
direct fetch so only the standard, widely-documented TD Setup counting rule
itself (not a specific numeric backtest) was used to seed parameters.

## Grid test (Step 6)

`param_grid = {setup_count: [8,9], exit_sma_window: [5,10,20], max_hold_days: [5,8]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3,
2019-01-01 to 2026-09-01. 144 total cells.

- pass_fraction: **0.097** (14/144)
- by_asset_class: equity 14/72, crypto 0/72
- by_vol_regime: low 2/48, mid 0/48, **high 12/48**
- best_cell: QQQ, setup_count=8, exit_sma_window=10, max_hold_days=8, **high-vol tercile**, Sharpe 1.835
- worst_cell: same config, **mid-vol tercile**, Sharpe -1.323

The "best" grid cell is a high-vol-tercile slice, not representative of the
full sample — same pattern flagged repeatedly elsewhere in this log (e.g.
2026-09-03-009, -010).

## Full-sample validators (Step 7) — grid-best config (setup_count=8, exit_sma_window=10, max_hold_days=8)

| Symbol | Sharpe | MDD | Net Sharpe (10bps, N trades) |
|---|---|---|---|
| QQQ | 0.670 (fail, thr 1.0) | 0.105 (pass, thr 0.25) | 0.624 (pass, thr 0.5, 23 trades) |
| SPY | 0.098 (fail, thr 1.0) | 0.305 (fail, thr 0.25) | 0.061 (fail, thr 0.5, 21 trades) |

Crypto rejected decisively at the grid stage (0/72 cells) — not re-tested at
full-sample validator stage.

## Decision: REJECTED (all asset classes)

QQQ misses Sharpe decisively (0.67 vs 1.0, a 33% shortfall — not a
near-miss); SPY fails Sharpe, MDD, and net-Sharpe simultaneously. Walk-forward
and parameter-sensitivity skipped per Step 7 minimum-subset guidance (Sharpe
already fails decisively on the primary config, consistent with prior
practice in this log e.g. 2026-09-04-026/-028).
