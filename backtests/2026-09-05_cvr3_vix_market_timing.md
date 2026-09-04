# CVR3 VIX Market Timing (Larry Connors & Dave Landry)

**Hypothesis:** Per StockCharts ChartSchool's exact rule disclosure, the
CVR3 strategy uses $VIX as a fear/complacency gauge to time mean-reversion
entries in the S&P 500. Buy signal requires all 3 VIX-only conditions to
align same-day: (1) VIX daily low > VIX 10d SMA, (2) VIX close >=
1.10x VIX 10d SMA (10% above), (3) VIX closes below its own open. Exit on
VIX crossing back below the prior day's 10d SMA (source's rule), a 2-4 day
hold, or a max_hold_days safety backstop.

Source: https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/cvr3-vix-market-timing

Novelty: first VIX-signal-driven CVR3 strategy in this repo; distinct from
the VIX Bollinger Band breakout (2026-09-04-103, rejected) and VIX3M
term-structure (2026-09-04-157, rejected) strategies already tested — this
uses VIX's own 10-day SMA relationship and intraday bar-color logic rather
than Bollinger Bands or a term-structure ratio.

**Bonus fix this iteration:** while building this strategy, discovered and
fixed the SAME tz-aware-Timestamp bug (from the ccxt_provider fix earlier
this run, commit 9f5a7db) was ALSO present in
`src/quant_agent/data/market_data.py::MarketDataService.get()` and
`src/quant_agent/data/cache.py::ParquetCache.covers/read()` — any strategy
combining two different asset symbols in one `generate_signals` call (like
this one, which internally re-fetches ^VIX using timestamps derived from
`price_df.index`) triggered it. Consolidated the fix into one shared
`to_utc_timestamp()` helper in `cache.py`, reused by `market_data.py` and
`ccxt_provider.py`.

## Step 6 — Grid summary

Grid: `vix_pct_above in {0.05,0.10}`, `max_hold_days in {4,6}`, symbols
QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 48 total cells.

- pass_fraction: 0.167 (8/48)
- by_asset_class: equity 8/24 passed; crypto 0/24 (genuine underperformance
  -- VIX is an S&P-options-implied-vol index, has no natural crypto
  economic link; this cross-asset test was a deliberate generalization
  stress-test per this repo's grid convention, not a claim of applicability)
- by_vol_regime: low 8/16, mid 0/16, high 0/16
- best_cell: vix_pct_above=0.05, max_hold_days=6, QQQ, low-vol, Sharpe 1.91

## Step 7 — Single-config validation (vix_pct_above=0.05, max_hold_days=6)

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.248 FAIL | -0.044 FAIL |
| Max drawdown (<=0.25) | 0.328 FAIL | 0.403 FAIL |
| Net-of-cost Sharpe (>=0.5, 10bps/trade) | 0.140 FAIL | -0.160 FAIL |
| Param sensitivity relative_std (<=0.5, vix_pct_above in {0.05,0.10}) | 4.119 FAIL | 0.797 FAIL |
| num_trades | 91 | 91 |
| Walk-forward | not run — same vectorbt limitation as prior entries this run. |

## Step 8 — Decision

**Rejected, decisively.** Every validator fails on both symbols at the
grid-best config, and the strategy fails MDD particularly badly (SPY 0.403
-- the worst MDD of any strategy tested this run). Parameter sensitivity
is catastrophically unstable on QQQ (relative_std 4.12 -- the mean Sharpe
across the 2-value vix_pct_above sweep is nearly zero with a much larger
std, meaning the sign/magnitude of the edge flips entirely with a tiny
parameter change). This is a clear overfitting/instability failure, not
just a full-sample-dilution issue. Interesting secondary finding: unlike
this strategy's design intent (S&P/VIX specific), it also fails
comprehensively on QQQ despite QQQ/SPY correlation, suggesting the specific
VIX threshold rule doesn't generalize even within equities. Crypto
rejected 0/24 (no VIX-crypto economic link, as expected). SPY MDD (0.403)
is the worst drawdown recorded in this run's knowledge base entries.
