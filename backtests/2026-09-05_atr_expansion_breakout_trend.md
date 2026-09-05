# ATR-expansion volatility breakout with trend filter (rejected)

**Hypothesis:** Per quantifiedstrategies.com's "Volatility ATR Bands
Strategy With a 33-Year Backtest" article, entries require (1) an explicit
ATR-expansion signal (ATR jumping above its own rolling average by
`atr_expansion_ratio`), (2) price breaking the upper EMA+ATR band, and (3) a
long-term SMA trend filter; exit is a mean-reversion signal (price crossing
back through the EMA basis) or trend-filter break/time-stop.

Source: https://www.quantifiedstrategies.com/volatility-atr-bands-strategy/
(fetched via `browser_exec` after Google search fallback — `web_search`
failed repeatedly this iteration with a DDGS/rustls TLS error).

Novelty: distinct from all prior Keltner/ATR strategies in this repo
(2026-09-03-016 plain Keltner breakout, 2026-09-04-091/126 TTM/LazyBear
squeeze, 2026-09-04-116 Chande Kroll, 2026-09-04-132 FRAMA+ATR band,
2026-09-04-092 dual-ROC+ATR-stop) — none of those gate entry on the raw ATR
VALUE crossing above its own rolling average; this is the source's
distinguishing design choice.

## Step 6 — Grid summary

Grid: `atr_expansion_ratio in {1.15,1.25,1.4}`, `atr_mult in {1.5,2.0}`,
`max_hold_days in {15,20}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 144 total cells.

- pass_fraction: 0.014 (2/144)
- by_asset_class: equity 2/72 passed; crypto 0/72 (decisive)
- by_vol_regime: low 2/48, mid 0/48, high 0/48
- best_cell: atr_expansion_ratio=1.15, atr_mult=1.5, max_hold_days=15, QQQ,
  low-vol, Sharpe 1.43

## Step 7 — Single-config check (best grid params: atr_expansion_ratio=1.15, atr_mult=1.5, max_hold_days=15)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (QQQ, full-period) | ❌ | -0.28 | ≥ 1.0 |
| Sharpe ratio (SPY, full-period) | ❌ | -0.05 | ≥ 1.0 |
| Max drawdown (QQQ) | ✅ | 16.7% | ≤ 25% |
| Max drawdown (SPY) | ✅ | 6.4% | ≤ 25% |

Full-period Sharpe is decisively negative on both equity symbols despite
one narrow low-vol grid cell looking attractive (1.43 on QQQ low-vol
tercile only) — same pattern as several prior rejected near-misses in this
repo (e.g. Laguerre RSI 2026-09-05-053): the ATR-expansion + price-breakout
+ trend-filter combination fires too rarely and/or at the wrong times
across the full sample to produce a positive full-period edge, even though
it isolates a positive slice within one volatility tercile. Skipped
walk-forward/parameter-sensitivity since the full-period Sharpe failure is
already decisive (`suggested_workload=max` this iteration, but no further
validators would change the outcome).

## Decision: **REJECT** (both equity and crypto; narrow low-vol-only artifact, not a real edge)
