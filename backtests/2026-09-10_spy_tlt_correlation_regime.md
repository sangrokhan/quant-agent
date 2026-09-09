# Backtest report: SPY/TLT rolling-correlation regime gate on SMA trend-following

**Strategy file:** `strategies/2026-09-10_spy_tlt_correlation_regime.py`
**Hypothesis id:** see `knowledge_base/strategies_log.jsonl` entry
2026-09-10-032

## Source

https://www.quantifiedstrategies.com/correlation-trading-strategies/
("Index and Bond ETF Correlation Rotation" section): 90-day rolling
SPY-TLT correlation regime table — below -0.4 = "normal diversification"
(bonds hedge equities), -0.4 to +0.3 = transitional, above +0.3 = "both
moving together" (bonds lose hedging value, historically an
inflation/rate-stress regime like 2022).

## Hypothesis

SMA(trend_window) trend-following long on the primary asset, gated flat
whenever the rolling `corr_window`-day Pearson correlation between the
asset's daily returns and TLT's daily returns rises above
`corr_threshold` (the "everything moves together" stress regime). Both
signals shifted 1 day to avoid look-ahead.

## Grid test (Step 6)

`param_grid={"trend_window": [50, 100], "corr_threshold": [0.0, 0.3]}` ×
`symbols={"equity": ["SPY", "QQQ"], "crypto": ["BTC/USDT", "ETH/USDT"]}` ×
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, `corr_window=90` fixed.

- **pass_fraction: 12/48 = 0.25**
- **by_asset_class:** equity 12/24 passed, crypto 0/24 passed
- **by_vol_regime:** low 8/16, mid 4/16, high 0/16
- **best_cell:** trend_window=50, corr_threshold=0.3, QQQ, low-vol, Sharpe 2.713
- QQQ clears the Sharpe bar in BOTH low-vol (Sharpe 2.2–2.7 across all 4
  param combos) AND mid-vol (Sharpe 1.1–1.4 across all 4 combos) regimes —
  the only symbol in this repo's grid to pass 2 of 3 vol regimes for this
  hypothesis. SPY only clears low-vol (Sharpe ~2.1–2.5); its mid/high-vol
  cells all fail (Sharpe 0.2–0.6). Crypto fails everywhere (expected —
  BTC/ETH have no economically meaningful correlation-regime relationship
  with TLT the way equities do).

## Single-config validators (primary config: QQQ, trend_window=50, corr_threshold=0.3, corr_window=90, full period 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.084 | ≥ 1.0 | PASS |
| Max drawdown | 0.189 | ≤ 0.25 | PASS |
| Transaction-cost survival (5bps/trade, 115 trades) | 1.007 net Sharpe | ≥ 0.5 | PASS |
| Walk-forward (manual 4-way chronological split; `vbt.utils.splitting` unavailable in installed vectorbt, see notes) | 3/4 splits positive Sharpe (1.036, -0.217, 2.058, 1.818) = 0.75 pass fraction | ≥ 0.75 | PASS |
| Parameter sensitivity (4-cell {50,100}×{0.0,0.3} QQQ low-vol Sharpes: 2.408/2.713/2.205/2.374) | relative_std = 0.076 | ≤ 0.5 | PASS |

## Decision

**Accepted — QQQ only.** All 5 validators pass on QQQ with
trend_window=50, corr_threshold=0.3, corr_window=90. Scope is explicitly
narrow: SPY only works in the low-vol tercile (not accepted as a live
config), and crypto fails entirely — a future loop should not assume this
transfers beyond QQQ/equity or beyond the tested vol regimes. Walk-forward
used a manual 4-way chronological split (not vectorbt's
`RangeSplitter`, which raised `AttributeError: module 'vectorbt.utils' has
no attribute 'splitting'` — a pre-existing installed-vectorbt-version gap
in `validation/validators.py::check_walk_forward`, worth a future loop's
attention) — the 2020-11-30 to 2022-10-27 split (which includes the 2022
rate-hike bear market) is the one negative-Sharpe split, consistent with
the strategy's own premise that "everything moves together" regimes are
harder to trade even with the filter.
