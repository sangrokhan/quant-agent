# Momentum + Volatility Regime Gate (blended 2-factor timing)

**Strategy file:** `strategies/2026-09-22_momentum_vol_regime_gate.py`
**Knowledge base id:** 2026-09-22-032

## Hypothesis

Per a Reddit r/algotrading post ("Update: 3-Factor Leveraged Model
(Momentum + Breadth + Volatility) Backtested 1999-2026", visited via
browser_exec Google SERP fallback -- web_search DDGS backend was
TLS-erroring on every query attempted this iteration), the author's own
disclosed mechanical rules for two of the three factors were:

- **Momentum gate**: exit to cash when a blended trend-health score
  (0.7 * 6-month trailing return + 0.3 * 12-month trailing return) drops
  below the risk-free rate, OR when the 3-month annualized return drops
  below zero.
- **Volatility crash-brake**: force an immediate exit to cash whenever
  trailing 6-month realized (annualized) volatility exceeds 30%.

Factor 2 (breadth-driven leverage-sizing dial swapping between 2x/3x
leveraged ETFs) requires cross-sectional market-breadth data (MMFI) not
available via this repo's single-symbol OHLCV `data/loaders.py`, and
leveraged-ETF products are out of scope per this repo's long-only,
no-leverage-product conventions -- so only Factors 1 and 3 were tested,
as a long/flat gate on the underlying asset itself.

## Grid test summary (params: risk_free_rate_annual in {0.0, 0.02},
vol_threshold in {0.25, 0.30, 0.40}; symbols QQQ/SPY/BTCUSDT/ETHUSDT;
vol_regime_splits=3; 72 total cells)

- **pass_fraction: 0.25** (18/72)
- **by_asset_class**: equity 18/36 (50%); crypto 0/36 (0%, decisive reject)
- **by_vol_regime**: low 12/24; mid 0/24; high 6/24
- **best_cell**: QQQ, risk_free_rate_annual=0.0, vol_threshold=0.4, low-vol
  regime, Sharpe 2.258
- **worst_cell**: BTC/USDT, vol_threshold=0.3, low-vol regime, Sharpe
  -0.256

## Full-sample validator suite (config: risk_free_rate_annual=0.0,
vol_threshold=0.4, 2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.873 (FAIL, thr 1.0) | 0.208 (pass, thr 0.25) | 0.806 (pass, thr 0.5) | 1.0 (pass, thr 0.75) | 0.164 (pass, thr 0.5) |
| SPY | 1.049 (PASS) | 0.179 (pass) | 0.945 (pass) | 0.75 (pass) | 0.032 (pass) |

## Decision

**Accept (SPY only)**, config `risk_free_rate_annual=0.0, vol_threshold=0.4`
-- all 5 validators pass. QQQ is a near-miss (Sharpe-only failure, all
other validators pass cleanly) -- worth a future retune iteration. Crypto
(BTC/USDT, ETH/USDT) decisively rejected in the grid (0/36 cells across
all params/vol regimes) -- the mechanism does not generalize to crypto's
different volatility/momentum dynamics without further adaptation.
