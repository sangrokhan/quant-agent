# Backtest report: FGI Rate-of-Change Momentum Trend (REJECTED, BTC/USDT)

**Strategy file:** `strategies/2026-09-22_fng_roc_momentum_trend.py`
**Hypothesis id:** 2026-09-22-109
**Source:** same FGI API (https://api.alternative.me/fng/) as prior FGI entries this cron trigger, but a distinct RATE-OF-CHANGE mechanic (not level).

## Hypothesis

Distinct from all prior FGI strategies this cron trigger (which use the FGI's absolute LEVEL), this tests the FGI's own N-day rate of change as a sentiment-momentum confirmation filter atop an SMA trend gate: long only when price>SMA(trend_window) AND FGI's roc_window-day change >= roc_threshold (sentiment actively improving, not just already at some level).

## Step 6 grid summary (roc_window in {5,7,14} x roc_threshold in {3,5,10}, 2019-01-01..2026-09-01, vol_regime_splits=3, symbols QQQ/SPY/BTC-USDT/ETH-USDT)

- **total cells:** 108, **passed:** 35, **pass_fraction: 0.324**
- **by_asset_class:** equity 13/54; crypto 22/54
- **by_vol_regime:** low 20/36; mid 7/36; high 8/36
- BTC/USDT at roc_window=14 (all 3 thresholds) passed all 3 vol-regime grid slices (3/3) -- looked like the best candidate config.

## Step 7 single-config validation (BTC/USDT, roc_window=14/roc_threshold=5.0, full 2019-2026 sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | pass | 1.49 | >= 1.0 |
| Max drawdown | **FAIL** | 0.335 | <= 0.25 |
| Transaction cost survival (10bps/trade, 305 trades) | pass | net Sharpe 1.26 | >= 0.5 |
| Walk-forward (4 splits) | pass | 1.0 (4/4 positive: 2.34, 1.03, 1.34, 0.53) | >= 0.75 |
| Parameter sensitivity (9-cell BTC grid) | pass | relative_std 0.256 | <= 0.5 |

Despite passing all 3 vol-regime grid slices individually and 4/5 full-sample validators, the full-sample max drawdown decisively fails (0.335 vs 0.25 threshold) -- the vol-tercile slicing in Step 6 apparently splits out the single worst drawdown episode into a regime the grid didn't separately flag as failing, masking it from the per-regime pass/fail view. This is a useful lesson: per-vol-regime grid passes don't guarantee full-sample drawdown control when a single large drawdown straddles regime boundaries.

## Decision: REJECTED

Fails the max-drawdown validator on its best grid-selected config (0.335 > 0.25) despite good Sharpe/walk-forward/parameter-sensitivity. Strategy file and this report kept as a record of a rejected attempt -- the FGI-rate-of-change mechanic itself may still be worth a future revisit with an added explicit stop-loss or the high-vol kill-switch pattern from 2026-09-22-108 to control the drawdown directly, rather than relying on the trend-gate alone.
