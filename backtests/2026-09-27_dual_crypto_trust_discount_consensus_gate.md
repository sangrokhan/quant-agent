# Backtest Report: Dual Crypto-Trust-Discount Consensus Gate (GBTC + ETHE)

**Strategy file:** `strategies/2026-09-27_dual_crypto_trust_discount_consensus_gate.py`
**Hypothesis ID:** 2026-09-27-097 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

This cron trigger's earlier iteration (2026-09-27-095) used the GBTC/BTC
market-price ratio's rolling z-score alone as a single risk-off proxy gate
(accepted QQQ+SPY). Grayscale's Ethereum Trust (ETHE, per
companiesmarketcap.com/YCharts confirming its premium/discount history,
`web_search`) provides an INDEPENDENT second crypto-trust discount signal
tracking a different underlying asset (ETH vs BTC). This strategy requires
BOTH proxies (GBTC/BTC ratio z-score AND ETHE/ETH ratio z-score) to
simultaneously signal stress (an AND-gate CONSENSUS) before flattening a
primary asset's SMA trend-following signal — the rationale being that a
genuine market-wide crypto liquidity/capitulation event should show up in
BOTH trusts' relative pricing simultaneously, filtering out idiosyncratic
single-trust noise. Distinct from 2026-09-27-095's single-ratio gate via
this dual-independent-signal consensus mechanic.

## Single-config validation (2019-01-01 to 2026-09-01)

| Symbol | Config | Sharpe | MDD | Net Sharpe (TC) | Walk-fwd | Param sens. | Result |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=30, zscore_window=120, low_z=-1.0, min_hold_days=10 | 1.553 ✅ | 0.143 ✅ | 1.310 ✅ | 1.00 ✅ | 0.081 ✅ | **PASS** |
| SPY | trend_window=30, zscore_window=60, low_z=-0.5, min_hold_days=10 | 1.442 ✅ | 0.093 ✅ | 1.022 ✅ | 1.00 ✅ | 0.158 ✅ | **PASS** |

All 5 validators pass cleanly for BOTH QQQ and SPY, with strong margins on
every metric — the strongest single-config result of this cron trigger
(highest Sharpe, lowest MDD, and net-of-cost Sharpe actually EXCEEDING
gross Sharpe threshold on both symbols, i.e. `min_hold_days` hysteresis
alone was sufficient with no separate rescue needed, unlike this trigger's
prior single-ratio GBTC/BTC and COIN/BTC strategies which both required a
narrower rescue search).

## Grid-test summary (Step 6)

Grid: `trend_window ∈ {30,50,80}`, `zscore_window ∈ {60,90,120}`,
`low_z_threshold ∈ {-0.5,-1.0,-1.5}` × symbols `{QQQ,SPY}` (equity),
`{BTC/USDT,ETH/USDT}` (crypto) × vol_regime_splits=3, using
`validation/grid_test.py::run_strategy_grid` (no `min_hold_days` in grid).

- **Overall pass_fraction: 0.284** (92/324 cells).
- **By asset class:** equity 81/162 (0.500); crypto 11/162 (0.068).
- **By vol regime:** low 64/108 (0.593); mid 23/108 (0.213); high 5/108
  (0.046) — second cron-trigger iteration (after COIN/BTC) with any
  non-zero high-vol-regime pass rate.
- **Best cell:** equity QQQ, low-vol, Sharpe 2.938 at trend_window=50/
  zscore_window=120/low_z_threshold=-1.5.

## Decision

**Accept: QQQ and SPY** (both symbols, per-symbol tuned configs above) —
the cleanest, strongest-margin acceptance of this cron trigger. **Reject
crypto** (BTC/USDT, ETH/USDT — 11/162 grid pass, not pursued for
acceptance; crypto's own extreme volatility profile has consistently
failed the MDD bar across every cross-asset-proxy construction tested this
trigger, per 2026-09-27-095/096's identical crypto-rejection pattern).
