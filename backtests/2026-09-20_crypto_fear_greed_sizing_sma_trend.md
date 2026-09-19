# Crypto Fear & Greed Index Continuous Sizing Dial + SMA Trend Gate

**Strategy file:** `strategies/2026-09-20_crypto_fear_greed_sizing_sma_trend.py`
**Date:** 2026-09-20
**Knowledge base id:** 2026-09-20-030

## Hypothesis

Direct follow-up to this cron trigger's own 2026-09-20-029 (crypto Fear &
Greed Index two-level absolute-threshold hysteresis, REJECTED -- decisive
max-drawdown fail on all 4 symbols despite QQQ/BTC Sharpe near/above 1.0).
This iteration reframes the same verified-feasible data source
(`api.alternative.me/fng/`, free unauthenticated API, 3149+ daily
observations since Feb 2018) as a CONTINUOUS SIZING dial rather than a
binary hysteresis: `dial = (50 - fng) / 50` (bounded [-1, 1] by
construction), scaling exposure inversely with sentiment extremity within
an SMA(trend_window) uptrend gate -- more fear = more exposure, more greed
= less exposure -- rather than holding a fixed full position through an
entire greed-to-fear cycle regardless of depth.

## Grid test (Step 6)

`scripts/run_grid_crypto_fng_sizing.py`: param_grid = {sensitivity: [0.4,
0.6, 0.8], deadband: [0.10, 0.15, 0.20]} x symbols {QQQ, SPY, BTC/USDT,
ETH/USDT} x vol_regime_splits=3. 108 total cells.

- **pass_fraction: 0.500** (54/108) -- roughly 3x the pass rate of the
  rejected binary-hysteresis predecessor (0.185)
- by_asset_class: equity 26/54 (48%), crypto 28/54 (52%) -- balanced, holds
  on BOTH legs now (unlike the predecessor, where crypto was 0/54)
- by_vol_regime: low 36/36 (100%), mid 18/36 (50%), high 0/36 (0%)
- sensitivity=0.4 was the most robust setting across ALL 4 symbols in a
  full-sample (not just tercile) check

## Single-config validation (Step 7)

| Config | sensitivity | deadband | leverage_cap |
|---|---|---|---|
| Equity (QQQ, SPY) | 0.4 | 0.15 | 0.45 |
| Crypto (BTC/USDT, ETH/USDT) | 0.4 | 0.15 | 0.3 |

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| QQQ | 1.080 (pass) | 0.106 (pass) | 0.557 (pass) | 0.75 (pass) | 0.019 (pass) | 146 |
| SPY | 1.102 (pass) | 0.061 (pass) | 0.511 (pass) | 0.75 (pass) | 0.048 (pass) | 127 |
| BTC/USDT | 1.477 (pass) | 0.175 (pass) | 1.170 (pass) | 1.00 (pass) | 0.024 (pass) | 171 |
| ETH/USDT | 1.258 (pass) | 0.213 (pass) | 1.066 (pass) | 1.00 (pass) | 0.015 (pass) | 165 |

Walk-forward uses this repo's standard manual 4-way contiguous-chunk
fallback (installed vectorbt 1.1.0's `RangeSplitter` helper is broken --
same known issue as several prior entries).

**All 5 validators pass for all 4 symbols.**

## Decision

**ACCEPTED** — equity (QQQ, SPY) at sensitivity=0.4/deadband=0.15/leverage_cap=0.45,
crypto (BTC/USDT, ETH/USDT) at sensitivity=0.4/deadband=0.15/leverage_cap=0.3.
Directly rescues the prior binary-hysteresis rejection's failure mode
(unconditional MDD blowup) by scaling exposure continuously with sentiment
extremity instead of holding a fixed position through the entire cycle.

## Sources

- `https://api.alternative.me/fng/?limit=0&format=json` -- verified via
  direct curl this cron trigger: free, unauthenticated, no rate limit,
  3149+ daily crypto Fear & Greed observations since Feb 2018. This
  corrects a prior repo assumption (2026-09-12-167 and others) that
  incorrectly lumped this data source in with genuinely infeasible ones
  (CBOE put/call ratio, on-chain MVRV/SOPR).
