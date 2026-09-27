# Backtest Report: Triple Crypto-Proxy Majority-Vote Stress Gate

**Strategy file:** `strategies/2026-09-27_triple_proxy_majority_vote_gate.py`
**Hypothesis ID:** 2026-09-27-099 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

This cron trigger's iteration 2026-09-27-097 required BOTH GBTC/BTC and
ETHE/ETH ratio z-scores to simultaneously signal stress (strict AND-of-2)
before flattening a primary asset's trend signal (accepted QQQ+SPY, the
trigger's strongest margins so far). This iteration tests a distinct
aggregation rule: a 3-proxy MAJORITY VOTE (>=2 of 3 must signal stress),
adding MSTR/BTC (already independently validated as a cross-asset signal
in 2026-09-20-040/041, there used as a ratio-LEVEL trend gate rather than
a z-score stress vote) as a third leg alongside GBTC/BTC and ETHE/ETH. The
majority-vote rule tolerates one dissenting proxy while still acting on
2-of-3 consensus, trading strictness for sensitivity relative to the
AND-of-2 sibling.

## Single-config validation (2019-01-01 to 2026-09-01)

| Symbol | Config | Sharpe | MDD | Net Sharpe (TC) | Walk-fwd | Param sens. | Result |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=30, zscore_window=120, low_z=-1.0, min_hold_days=10 | 1.485 ✅ | 0.143 ✅ | 1.217 ✅ | 1.00 ✅ | 0.156 ✅ | **PASS** |
| SPY | (identical shared config) | 1.382 ✅ | 0.093 ✅ | 1.005 ✅ | 1.00 ✅ | 0.107 ✅ | **PASS** |

All 5 validators pass cleanly for BOTH QQQ and SPY at an IDENTICAL shared
config (no per-symbol retuning needed) — a nice practical property versus
this trigger's other proxy strategies, which typically needed per-symbol
tuned configs.

## Grid-test summary (Step 6)

Grid: `trend_window ∈ {30,50,80}`, `zscore_window ∈ {60,90,120}`,
`low_z_threshold ∈ {-0.5,-1.0,-1.5}` × symbols `{QQQ,SPY}` (equity),
`{BTC/USDT,ETH/USDT}` (crypto) × vol_regime_splits=3, using
`validation/grid_test.py::run_strategy_grid` (no `min_hold_days` in grid).

- **Overall pass_fraction: 0.275** (89/324 cells).
- **By asset class:** equity 79/162 (0.488); crypto 10/162 (0.062).
- **By vol regime:** low 63/108 (0.583); mid 18/108 (0.167); high 8/108
  (0.074) — the HIGHEST high-vol-regime pass count of any strategy this
  cron trigger (previous best: 5/108, COIN/BTC strategy), consistent with
  the majority-vote's sensitivity trade-off catching more genuine stress
  episodes that a stricter AND-of-2/single-ratio gate would miss.
- **Best cell:** equity QQQ, low-vol, Sharpe 3.200 at trend_window=50/
  zscore_window=90/low_z_threshold=-1.0.

## Comparison to AND-of-2 sibling (2026-09-27-097)

| Metric | AND-of-2 (GBTC+ETHE) | Majority-vote (GBTC+ETHE+MSTR) |
|---|---|---|
| Grid pass_fraction | 0.284 | 0.275 |
| High-vol-regime pass count | 5/108 | 8/108 |
| QQQ full-sample Sharpe | 1.553 | 1.485 |
| SPY full-sample Sharpe | 1.442 | 1.382 |
| Shared config across symbols | No (per-symbol tuned) | Yes (identical config both symbols) |

The two constructions are close in headline performance; majority-vote
trades a small amount of peak Sharpe for (a) better high-vol-regime
robustness and (b) a single shared config across symbols — both arguably
practical advantages, though not decisively superior on raw Sharpe/MDD.

## Decision

**Accept: QQQ and SPY** (identical shared config, both symbols pass all 5
validators cleanly). **Reject crypto** (BTC/USDT, ETH/USDT — 10/162 grid
pass, consistent with this trigger's repeated crypto-MDD-failure pattern
across every cross-asset-proxy construction tested).
