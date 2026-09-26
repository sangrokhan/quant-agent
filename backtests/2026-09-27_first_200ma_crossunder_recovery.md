# Backtest Report: First 200MA Cross-Under Recovery Signal (Single-Symbol Proxy)

**Strategy file:** `strategies/2026-09-27_first_200ma_crossunder_recovery.py`
**Date:** 2026-09-27
**Source:** https://alvarezquanttrading.com/blog/the-30-selloff-signal-what-history-tells-us-about-market-recoveries/
(Cesar Alvarez, March 2025), read via `browser_exec`.

## Hypothesis

The first day the S&P 500 closes under its 200-day SMA after 6+ months
above it tends to precede above-average subsequent returns, especially
combined with elevated cross-sectional breadth weakness (% of stocks 30%+
off their 52-week high). Adapted single-symbol proxy: use the primary
asset's OWN drawdown from its trailing 252-day high as a substitute
breadth-severity gauge, combined with the exact "first cross-under after
sustained 6-month uptrend" event trigger (fully implementable on
single-symbol OHLCV, unlike the source's cross-sectional breadth stat).

## Grid test summary (Step 6)

Grid: `hold_days in [63,126,252]` x `min_drawdown_pct in [0.0, 0.10]` x
equity {QQQ, SPY} + crypto {BTC/USDT, ETH/USDT} x 3 vol-regime terciles,
2010-2026.

- **Overall pass_fraction: 0.139 (10/72 cells)**
- **by_asset_class:** equity 8/36 (0.222); crypto 2/36 (0.056)
- **by_vol_regime:** low 5/24; mid 5/24; high 0/24
- **best_cell:** SPY low-vol, `hold_days=252, min_drawdown_pct=0.0`, Sharpe 1.59

## Full-sample check (all configs, QQQ/SPY, 2010-2026)

| Symbol | hold_days | min_drawdown_pct | Sharpe | MDD |
|---|---|---|---|---|
| QQQ | 252 | 0.0 | 0.683 (best) | 0.369 |
| QQQ | 126 | 0.0 | 0.562 | 0.334 |
| SPY | 252 | 0.0 | 0.623 | 0.287 |
| SPY | 126 | 0.0 | 0.557 | 0.287 |
| (all `min_drawdown_pct=0.10` configs) | -- | -- | 0.06-0.30 | -- |

## Decision: **REJECTED (decisive)**

Best full-sample Sharpe (QQQ, `hold_days=252, min_drawdown_pct=0.0`) is
only 0.683 -- well short of the 1.0 threshold -- and MDD is also
unacceptably high (0.369). Adding the drawdown severity gate
(`min_drawdown_pct=0.10`, intended to mimic the source's "bigger
sell-off -> bigger subsequent edge" bucket finding) makes results WORSE
across every config tested, not better -- the single-symbol drawdown
proxy does not reproduce the source's cross-sectional breadth signal's
behavior. This confirms the source's own explicit caveat ("this signal
has occurred only 17 times since 1991... not a big sample size") -- the
effect the source found relies on genuine cross-sectional breadth
information (how many DIFFERENT stocks are broken down, not how far the
INDEX itself is down), which cannot be faithfully reconstructed from a
single symbol's own price history. Not worth pursuing further without a
genuine breadth data source (which this repo's yfinance/ccxt loaders do
not provide).
