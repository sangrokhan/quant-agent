# Backtest report: Crypto Fear & Greed Index Contrarian (REJECTED)

**Strategy file:** `strategies/2026-09-22_crypto_fear_greed_contrarian.py`
**Hypothesis id:** 2026-09-22-104
**Source:** alternative.me Crypto Fear & Greed Index, https://alternative.me/crypto/fear-and-greed-index/ and free JSON API https://api.alternative.me/fng/?limit=0&format=json (history back to 2018-02-01). Source's own stated thesis: "extreme fear can be a sign that investors are too worried -- that could be a buying opportunity."

## Hypothesis

Long-only contrarian entry when the daily Crypto Fear & Greed Index (FNG, 0-100) drops to/below an "extreme fear" threshold; exit once sentiment normalizes back above an exit threshold, or after a max holding period. Tested on both crypto (BTC/USDT, ETH/USDT -- direct sentiment on the asset) and equity index ETFs (QQQ, SPY -- as a broad risk-sentiment proxy).

## Step 6 grid summary (extreme_fear_threshold in {15,20,25} x exit_threshold in {40,50,60}, 2019-01-01..2026-09-01, vol_regime_splits=3, symbols QQQ/SPY/BTC-USDT/ETH-USDT)

- **total cells:** 108, **passed:** 9, **pass_fraction: 0.083**
- **by_asset_class:** equity 9/54 passed; **crypto 0/54 passed** (FNG signal has zero edge on the crypto assets it's actually derived from -- decisive negative result for the primary hypothesis)
- **by_vol_regime:** low-vol 9/36 passed; mid-vol 0/36; high-vol 0/36 (only survives in the calmest regime slice, exactly where almost any long-biased strategy tends to pass trivially given secular uptrend drift)
- **best cell:** QQQ, extreme_fear_threshold=15/exit_threshold=60, low-vol regime, Sharpe 1.30
- **worst cell:** SPY, extreme_fear_threshold=20/exit_threshold=40, mid-vol regime, Sharpe -1.15

## Step 7 single-config validation (QQQ, best grid config: extreme_fear_threshold=15, exit_threshold=60, max_hold_days=30, full 2019-2026 sample, not vol-sliced)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.41 | >= 1.0 |
| Max drawdown | pass | 0.218 | <= 0.25 |

Full-sample Sharpe (0.41) decisively fails despite the isolated low-vol-tercile grid cell showing Sharpe 1.30 -- the low-vol slice cherry-picks the calmest, most trivially-long-biased sub-period. Walk-forward/parameter-sensitivity/transaction-cost validators were not run given the decisive full-sample Sharpe failure (light-enough evidence to reject without further compute).

## Decision: REJECTED

Fails the primary full-sample Sharpe validator on its best grid-selected config; fails on 0/54 crypto cells (the asset class the sentiment index is actually derived from, undermining the core causal story); only passes narrowly in equity low-vol-regime slices, which is likely just secular uptrend drift rather than a genuine sentiment-contrarian edge. Strategy file and this report are kept as a record of a rejected attempt.
