# Backtest Report: COIN/BTC Ratio ROC Crossover Confirmation Gate

**Strategy file:** `strategies/2026-09-27_coin_btc_roc_crossover_gate.py`
**Hypothesis ID:** 2026-09-27-096 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

Coinbase (COIN)'s direct listing (April 14, 2021) coincided almost exactly
with a Bitcoin cycle top, a pattern discussed in retrospectives (per
cryptoslate.com's "New Bitcoin 'top signal' is in" and stockanalysis.com's
IPO-to-impact overview, found via `web_search`) as reflecting a structural
link between crypto-native equity sentiment and the underlying asset's own
cycle. COIN's revenue is overwhelmingly trading-fee-driven, so its stock
price should lead/confirm shifts in crypto trading ACTIVITY/volume,
distinct from this repo's existing MSTR (passive balance-sheet holder,
ratio-LEVEL gate) and MARA (miner, ratio-Z-SCORE overshoot gate) proxy
constructions. This strategy computes the rolling ROC (momentum) of the
COIN/BTC price ratio and its own EMA signal line; a bullish crossover
(ROC > signal) confirms accelerating crypto-equity enthusiasm relative to
BTC's own move, gating a primary asset's SMA(trend_window) trend-following
signal.

## Single-config validation (2021-05-01 to 2026-09-01, post-COIN-IPO)

| Symbol | Config | Sharpe | MDD | Net Sharpe (TC) | Walk-fwd | Param sens. | Result |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=30, roc_window=30, signal_window=15, min_hold_days=15 | 1.156 ✅ | 0.176 ✅ | 0.956 ✅ | 1.00 ✅ | 0.231 ✅ | **PASS** |
| SPY | trend_window=50, roc_window=30, signal_window=15, min_hold_days=20 | 1.095 ✅ | 0.096 ✅ | 0.836 ✅ | 0.75 ✅ | 0.505 ❌ | FAIL (param sensitivity, 0.505 vs 0.5 threshold) |

QQQ passes all 5 validators. SPY narrowly fails parameter_sensitivity
(0.505, just above the 0.5 threshold) — not pursued for rescue this
iteration. A raw daily-reevaluation config (no `min_hold_days`) passed
Sharpe/MDD/walk-forward/param-sensitivity on both symbols but failed
transaction-cost-survival (171/155 trades); adding `min_hold_days`
hysteresis (same rescue pattern as this cron trigger's GBTC/BTC strategy,
2026-09-27-095) reduced turnover to 55/49 trades and fixed TC-survival.

## Grid-test summary (Step 6)

Grid: `trend_window ∈ {30,50,80}`, `roc_window ∈ {10,20,30}`,
`signal_window ∈ {5,10,15}` × symbols `{QQQ,SPY}` (equity), `{BTC/USDT,
ETH/USDT}` (crypto) × vol_regime_splits=3, using
`validation/grid_test.py::run_strategy_grid` (no `min_hold_days` in the
grid).

- **Overall pass_fraction: 0.349** (113/324 cells) — the highest grid
  pass_fraction of this cron trigger's iterations (previous best: 0.315,
  GBTC/BTC strategy).
- **By asset class:** equity 75/162 (0.463); crypto 38/162 (0.235) — the
  best crypto grid result of this trigger, though full-sample crypto sweep
  showed MDD 0.21-0.40 (BTC) / 0.28-0.39 (ETH), consistently above the
  0.25 threshold even at Sharpe>1.0 configs.
- **By vol regime:** low 86/108 (0.796); mid 22/108 (0.204); high 5/108
  (0.046) — the first NON-ZERO high-vol-regime pass rate of this cron
  trigger's iterations (5 cells), a modest improvement over the universal
  high-vol failure seen elsewhere.
- **Best cell:** equity SPY, low-vol, Sharpe 3.615 at trend_window=30/
  roc_window=20/signal_window=5.

## Decision

**Accept: QQQ only** (`trend_window=30, roc_window=30, signal_window=15,
min_hold_days=15`). **Reject SPY** (parameter_sensitivity 0.505, narrow
miss, not rescued this iteration) and **crypto** (BTC/USDT, ETH/USDT —
decisive MDD failure at every tested config despite occasionally clearing
Sharpe, consistent with crypto's inherent tail-risk profile already seen
in this trigger's other cross-asset-proxy strategies).
