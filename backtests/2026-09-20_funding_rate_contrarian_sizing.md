# Perpetual Funding Rate Contrarian Continuous Sizing Dial (Crypto-only)

**Strategy file:** `strategies/2026-09-20_funding_rate_contrarian_sizing.py`
**Date:** 2026-09-20
**Knowledge base id:** 2026-09-20-031

## Hypothesis

Perpetual futures funding rate is paid periodically between long and short
holders to anchor the perpetual price to spot. Persistently positive
funding (longs paying shorts) signals crowded-long euphoria (contrarian
bearish); persistently negative funding (shorts paying longs) signals
crowded-short capitulation (contrarian bullish). This repo's prior funding-
rate attempt (2026-09-02-001, 1h-bar binary threshold mean-reversion) was
rejected, and several subsequent iterations (2026-09-09-009, 2026-09-10-084,
2026-09-18-118) incorrectly marked funding-rate strategies as
"feasibility-blocked, no data source in data/loaders.py". **This was
wrong** -- verified this iteration via direct `ccxt.binance()
.fetch_funding_rate_history(...)` calls (paginated via `since`) that
Binance's public funding-rate-history endpoint requires NO authentication
and has full history back to at least Jan 2020 for both BTC/USDT and
ETH/USDT perpetuals (same `ccxt` library this repo's `data/loaders.py`
already depends on for OHLCV).

This iteration reframes the contrarian funding signal as a CONTINUOUS
SIZING dial (rolling-sum aggregation of 8h funding observations to daily
granularity, then rolling z-scored + tanh-squashed + INVERTED so negative
funding => positive dial => more exposure) within an SMA(40) uptrend gate
-- the same construction pattern that has repeatedly rescued binary-
rejected indicators elsewhere in this repo.

Crypto-only by construction (no perpetual futures funding-rate mechanism
exists for SPY/QQQ), unlike this repo's usual 2-asset-class grid
convention.

## Grid test (Step 6, crypto-only)

`scripts/run_grid_funding_rate_sizing.py`: param_grid = {sensitivity: [0.4,
0.6, 0.8], deadband: [0.10, 0.15, 0.20]} x symbols {BTC/USDT, ETH/USDT}.
18 total cells (crypto-only scope, no vol-regime split applied at the
default leverage_cap=1.0 stage -- see note below).

- At default `leverage_cap=1.0`: Sharpe consistently strong (BTC 1.14-1.41,
  ETH 0.80-1.05) but MDD decisively fails everywhere (BTC 0.27-0.36, ETH
  0.40-0.49) -- same "needs a leverage-cap retune" pattern seen repeatedly
  for other crypto sizing dials in this repo.
- `sensitivity=0.4` was consistently the strongest setting for both symbols.

## Single-config validation (Step 7, leverage-cap retuned)

| Symbol | leverage_cap | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|---|
| BTC/USDT | 0.30 | 1.465 (pass) | 0.197 (pass) | 1.082 (pass) | 1.00 (pass) | 0.067 (pass) | 159 |
| ETH/USDT | 0.25 | 1.329 (pass) | 0.179 (pass) | 1.069 (pass) | 0.75 (pass) | 0.092 (pass) | 143 |

**All 5 validators pass for both symbols.**

## Decision

**ACCEPTED (crypto-only)** — BTC/USDT at sensitivity=0.4/deadband=0.15/
leverage_cap=0.3, ETH/USDT at sensitivity=0.4/deadband=0.15/leverage_cap=0.25.
No equity leg (funding rate is a perpetual-futures-specific mechanism, not
applicable to SPY/QQQ spot/equity).

## Sources / infrastructure note

Verified via direct `ccxt.binance().fetch_funding_rate_history()` calls
this cron trigger that Binance's public funding-rate-history endpoint is
freely accessible with no authentication, contradicting several prior
"feasibility-blocked" log entries (2026-09-09-009, 2026-09-10-084,
2026-09-18-118). Future iterations should NOT re-mark crypto perpetual
funding rate as infeasible.
