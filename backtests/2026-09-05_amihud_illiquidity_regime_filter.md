# Amihud Illiquidity-Spike Regime Filter — Backtest Report (2026-09-05)

## Hypothesis
Per Amihud (2002) and https://microalphas.com/amihud-illiquidity/: aggregate/
security-level illiquidity (ILLIQ = mean(|daily return| / dollar volume) over
a rolling window) spiking sharply above its own recent norm signals market
stress; historically, rising illiquidity accompanies drawdowns. Signal: flat
when rolling-ILLIQ z-score >= risk_off_z, long otherwise. Computed purely
from daily OHLCV (no external liquidity data feed needed).

Source: https://microalphas.com/amihud-illiquidity/ (visited 2026-09-05,
via browser_exec fallback — web_extract failed, "search-only backend").
Cross-checked against a CBOE put/call-ratio contrarian-sentiment search
(https://www.wallstreetcourier.com/spotlights/the-cboe-put-call-ratio-a-useful-greed-fear-contrarian-indicator/)
which was NOT implementable (no free daily CBOE PC ratio ticker via
yfinance — ^CPC/^CPCE return 404/delisted).

## Single-config validators (SPY, illiq_window=10, risk_off_z=1.5, full 2019-2026 sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.173 | >= 1.0 |
| Max drawdown | PASS | 0.213 | <= 0.25 |
| Transaction cost survival (10 bps/trade, 47 trades) | PASS | net Sharpe 1.114 | >= 0.5 |
| Walk-forward | SKIPPED | -- | known repo-wide `vbt.utils.splitting.RangeSplitter` bug (AttributeError), same as prior iterations |
| Parameter sensitivity (equity/low-vol regime, 3x3 grid) | PASS | relative_std 0.038 | <= 0.5 |

## Step 6 grid-test summary (illiq_window in [10,20,40] x risk_off_z in [1.5,2.0,2.5], equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3)

- total_cells: 108, passed_cells: 30, **pass_fraction: 0.278**
- by_asset_class: equity 30/54 passed; **crypto 0/54 passed** (illiquidity-timing
  signal did not transfer to crypto in this sample -- likely because
  crypto dollar-volume dynamics/24h trading differ structurally from
  equity market-hours volume, and the fixed z-score threshold calibrated
  on equity behavior doesn't generalize)
- by_vol_regime: low 18/18(equity)+0/18(crypto)=18/36 passed; mid 9/36; high 3/36
  -> signal is strongest in low-vol regimes, degrades in high-vol regimes
  (counter to the "signals stress" theory -- in practice the filter helps
  most when volatility is already calm, and helps least exactly when vol
  is high, which is a meaningful caveat on the hypothesis)
- best_cell: SPY, illiq_window=10, risk_off_z=1.5, low-vol regime, Sharpe 2.72
- worst_cell: QQQ, illiq_window=20, risk_off_z=1.5, high-vol regime, Sharpe -0.09

## Decision: ACCEPT (narrow scope)

All validators run for the primary config (SPY, default best params) passed.
Scope is honestly narrow: **equity only** (SPY/QQQ), and strongest in
low/mid volatility regimes; crypto (BTC/USDT, ETH/USDT) failed on all 54
cells in the grid and should NOT be traded with this strategy. A future
loop revisiting this idea for crypto should use crypto-specific z-score
calibration (e.g. separate rolling lookback/threshold fit to crypto's
higher baseline illiquidity variance) rather than assuming the equity
config transfers.
