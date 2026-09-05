# Lumber/Gold ratio (Gayed RORO indicator) risk-on regime filter (rejected)

**Hypothesis:** Per quantifiedstrategies.com's "Lumber/Gold Ratio Trading
Strategy For Stocks And Bonds", Michael Gayed's WOOD/GLD ratio is a
Risk-On/Risk-Off (RORO) indicator (lumber = cyclical growth proxy, gold =
non-cyclical safe haven). The article's own modified rule: when the ratio
is higher than `lookback_days` (~1 month) ago, go risk-on (long); when
lower, go flat/defensive. Adapted here as a single-asset long/flat filter
(the source's own two-leg SPY/TLT rotation isn't expressible in this
repo's single-price_df generate_returns contract).

Source: https://www.quantifiedstrategies.com/lumber-gold-ratio-trading-strategy-for-stocks-and-bonds/
(`web_search` failed all session — DDGS/rustls TLS error — `browser_exec`
Google search + direct page read used).

Novelty: first Gayed-style lumber/gold RORO strategy in this repo —
distinct from SPY/TLT (2026-09-05-036), gold/silver, copper/gold, HYG/LQD,
yield-curve, DXY, MOVE-index regime filters already tested; lumber/gold
specifically encodes a housing-cycle/growth-vs-safe-haven signal.

## Step 6 — Grid summary

Grid: `lookback_days in {10,21,42,63}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 48 total cells.

- pass_fraction: 0.146 (7/48)
- by_asset_class: equity 7/24 passed; crypto 0/24 (decisive)
- by_vol_regime: low 6/16, mid 1/16, high 0/16
- best_cell: lookback_days=63, SPY, low-vol, Sharpe 1.96

## Step 7 — Single-config check (best grid params: lookback_days=63)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full-period) | ❌ 0.58 | ❌ 0.58 | ≥ 1.0 |
| Max drawdown | ❌ 26.1% | ✅ 21.0% | ≤ 25% |
| Transaction cost survival (10bps, 48 trades) | ✅ 0.51 | ❌ 0.48 | ≥ 0.5 |

Full-period Sharpe decisively misses the bar on both symbols despite the
attractive narrow low-vol grid cell (SPY 1.96) — the same recurring
"narrow-tercile-vs-negative-full-sample" failure pattern seen repeatedly
this session (Laguerre RSI 2026-09-05-053, ATR-expansion breakout
2026-09-05-055). QQQ additionally fails max drawdown outright. Crypto
rejected decisively (0/24).

## Decision: **REJECT** (both equity and crypto; narrow low-vol-only artifact, not a robust full-sample edge)
