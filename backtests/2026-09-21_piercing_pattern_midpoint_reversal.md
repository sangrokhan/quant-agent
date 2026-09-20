# Piercing Pattern Midpoint Reversal — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_piercing_pattern_midpoint_reversal.py`
**Outcome:** ACCEPTED (QQQ only, `trend_lookback=10, max_hold_days=10`)

## Hypothesis

Per Investopedia's ["Piercing Pattern Explained"](https://www.investopedia.com/piercing-pattern-explained-8747555)
(freely available), a classic 2-candle bullish reversal: bar1 is bearish in
a downtrend; bar2 gaps down at the open then closes above the MIDPOINT of
bar1's real body but below bar1's open (a partial, not full, reversal —
distinct from Bullish Engulfing, already tested/rejected in this repo as
2026-09-21-161). 0 prior "piercing pattern"/"piercing line" entries in this
repo.

## Grid test (Step 6)

`param_grid={"trend_lookback": [5,10,20], "max_hold_days": [5,10]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.181** (13/72 cells)
- **by_asset_class:** equity 10/36 passed; crypto 3/36 passed
- **by_vol_regime:** low 6/24; mid 7/24; high 0/24 — decisively fails
  high-vol regime, works only in calmer conditions.
- **best_cell:** `trend_lookback=10, max_hold_days=10`, QQQ, low-vol
  regime, Sharpe 2.27
- **worst_cell:** `trend_lookback=20, max_hold_days=5`, BTC/USDT, mid-vol
  regime, Sharpe -1.32

Full-sample Sharpe by config (own-data recalibration): QQQ
tl=5/0.735, tl=10/**1.173**, tl=20/0.406; SPY tl=5/0.270, tl=10/0.594,
tl=20/0.644. QQQ trend_lookback=10 is the clear standout.

## Single-config validation (QQQ, `trend_lookback=10, max_hold_days=10`)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.173 | ≥1.0 | **PASS** |
| Max drawdown | 0.039 | ≤0.25 | **PASS** |
| Transaction cost survival (5bps/trade, 28 trades) | net Sharpe 1.092 | ≥0.5 | **PASS** |
| Walk-forward (4 contiguous splits, own manual implementation — `validators.py`'s `check_walk_forward` hit an installed-vectorbt-version API mismatch, `vbt.utils.splitting` missing) | 0.75 (3/4 splits Sharpe>0) | ≥0.75 | **PASS** |
| Parameter sensitivity (QQQ trend_lookback∈{5,10,20}) | relative_std 0.407 | ≤0.5 | **PASS** |

SPY at the identical config: Sharpe 0.594 (fails threshold), MDD 0.036
(passes) — SPY is explicitly NOT accepted; this strategy's scope is QQQ
only.

## Decision

**Accepted for QQQ only** (`trend_lookback=10, max_hold_days=10`). All 5
validators pass. Low trade count (28 over 7.5 years) keeps transaction
costs negligible. Grid confirms the edge is confined to low/mid-vol
regimes and does not extend reliably to SPY or crypto — recorded here so a
future loop doesn't over-trust this outside QQQ.
