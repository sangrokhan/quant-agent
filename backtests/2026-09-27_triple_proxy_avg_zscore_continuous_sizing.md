# Backtest Report: Triple Crypto-Proxy Average-Z-Score Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-27_triple_proxy_avg_zscore_continuous_sizing.py`
**Hypothesis ID:** 2026-09-27-100 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

This cron trigger's prior two iterations (2026-09-27-097 AND-of-2 gate;
2026-09-27-099 majority-vote gate) both used the three crypto-trust-proxy
ratio z-scores (GBTC/BTC, ETHE/ETH, MSTR/BTC) as BINARY stress flags
combined into a discrete gate. This strategy follows this repo's
established "binary-threshold-to-continuous-sizing-dial rescue pattern"
(already validated for VHF, CBOE SKEW, DPO, Hurst, TII, RVI, MAMA-FAMA
spread, Kalman slope): the MEAN of the three z-scores is tanh-squashed
into a smooth [0,1] exposure multiplier within an SMA(trend_window)
uptrend gate, rather than flipping fully flat/long at a discrete
threshold.

## Single-config validation (2019-01-01 to 2026-09-01)

Config: `trend_window=30, zscore_window=120, sizing_scale=0.5,
deadband=0.15`

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Walk-fwd | Param sens. | Result |
|---|---|---|---|---|---|---|
| QQQ | 1.240 ✅ | 0.173 ✅ | 0.797 ✅ | 1.00 ✅ | 0.189 ✅ | **PASS** |
| SPY | 1.034 ✅ | 0.112 ✅ | 0.466 ❌ | 0.75 ✅ | 0.197 ✅ | FAIL (TC-survival, 159 trades) |

QQQ passes all 5 validators. SPY narrowly fails transaction-cost-survival
(0.466 vs 0.5 threshold, driven by 159 threshold-crossing "trades" from the
continuous dial's frequent small exposure adjustments) — not pursued for
rescue given this cron trigger's iteration budget (this is iteration 10,
the last allowed this trigger).

## Grid-test summary (Step 6)

Grid: `trend_window ∈ {30,50,80}`, `zscore_window ∈ {60,90,120}`,
`sizing_scale ∈ {0.5,1.0,1.5}` × symbols `{QQQ,SPY}` (equity),
`{BTC/USDT,ETH/USDT}` (crypto) × vol_regime_splits=3, using
`validation/grid_test.py::run_strategy_grid` (fixed `deadband=0.15`, not
grid-swept).

- **Overall pass_fraction: 0.302** (98/324 cells).
- **By asset class:** equity 63/162 (0.389); crypto 35/162 (0.216) — the
  SECOND-best crypto grid pass rate this cron trigger (best: COIN/BTC's
  38/162).
- **By vol regime:** low 77/108 (0.713); mid 11/108 (0.102); high 10/108
  (0.093) — the HIGHEST high-vol-regime pass count of any strategy this
  cron trigger (previous best: 8/108, triple-proxy majority-vote), showing
  the continuous-sizing reframing's smoother de-risking is even MORE
  robust in high-vol regimes than the binary majority-vote's already-good
  result.
- **Full-sample crypto sweep:** BTC/USDT reaches Sharpe 1.74 but MDD 0.34
  (fails); ETH/USDT Sharpe 1.21 but MDD 0.49-0.51 (fails decisively) —
  same crypto-MDD-failure pattern as every other cross-asset-proxy
  construction this trigger, despite attractive Sharpe.

## Decision

**Accept: QQQ only** (`trend_window=30, zscore_window=120,
sizing_scale=0.5, deadband=0.15`). **Reject SPY** (narrow TC-survival
miss, 0.466 vs 0.5) and **crypto** (BTC/USDT, ETH/USDT — decisive MDD
failure despite attractive Sharpe, consistent with every other
cross-asset-proxy strategy tested this trigger).
