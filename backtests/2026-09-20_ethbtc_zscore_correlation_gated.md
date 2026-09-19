# ETH/BTC z-score mean reversion, correlation-regime gated — REJECTED

**Hypothesis source:** BacktestEverything, "BTC-ETH Pair Trading: Backtesting
Crypto Relative Value Strategies"
(https://www.backtesteverything.com/blog/btc-eth-pair-trading-crypto-relative-value-backtest,
read via `browser_exec`, `web_extract` unavailable on this backend).

Source's own disclosed backtest: 60-day rolling z-score of the ETH/BTC ratio,
entry at |z|>2, exit at mean reversion or 3-std stop — unconditional Sharpe
0.71, 134 trades/8yr, 61% win rate. Source's own "Correlation Regime
Awareness" finding: filtering out periods where BTC-ETH correlation exceeds
0.85 (lockstep, no relative-value signal) improved their Sharpe to 0.91.

This repo already tested the UNCONDITIONAL version (2026-09-04-083,
rejected). This iteration adds the correlation-regime gate the source found
necessary, implemented as a self-contained proxy (ratio's own rolling
realized-vol-of-log-returns relative to its trailing history, standing in
for direct BTC/ETH correlation since `generate_signals(price_df, **params)`
only receives the single ETH/BTC ratio series per the grid-tester's
single-price-series calling contract) — distinct novel angle from the prior
unconditional rejection.

## Grid test (Step 6)

`entry_z ∈ {1.5, 2.0, 2.5} × corr_threshold ∈ {0.75, 0.85, 0.95}`,
symbols = ETH/BTC only (this is inherently a single cross-rate instrument,
not tradeable as separate equity/crypto asset classes), vol_regime_splits=3,
27 total cells.

- **pass_fraction: 0.111** (3/27 cells passed)
- **by_vol_regime:** low 0/9, mid 0/9, **high 3/9** — edge, if any, is
  entirely confined to the high-realized-vol tercile of the ratio itself.
- **best_cell:** entry_z=2.5, corr_threshold=0.75, high-vol tercile,
  Sharpe 1.42 (single tercile, not representative of full period)

## Single-config validation (Step 7) — entry_z=2.5, corr_threshold=0.75

| Validator | Result | Threshold | Pass? |
|---|---|---|---|
| Sharpe ratio (full period 2019-2026) | -0.084 | ≥ 1.0 | **FAIL** (decisive) |
| Max drawdown | 0.514 | ≤ 0.25 | **FAIL** (decisive) |
| Transaction-cost survival | net Sharpe -0.084 | ≥ 0.5 | **FAIL** |
| Walk-forward (4 contiguous splits, manual) | 1/4 splits positive (0.25) | ≥ 0.75 | **FAIL** |
| Parameter sensitivity (16-cell entry_z×corr_threshold sweep) | relative_std 0.521 | ≤ 0.5 | **FAIL** (narrowly) |

## Verdict: REJECTED

Full-period performance is decisively negative (Sharpe -0.08, MDD 51%) —
far worse than even the unconditional prior rejection (2026-09-04-083). The
correlation-regime gate as implemented here (a same-series realized-vol
proxy rather than true independently-computed BTC/ETH return correlation)
does not successfully isolate the source's intended "genuine divergence"
regime — it may instead be selecting for high-volatility whipsaw periods
where the z-score mean-reversion signal is least reliable, which would
explain both the poor full-period Sharpe and the failed walk-forward (only
1/4 splits profitable). This also reveals a genuine implementation
limitation of the current `generate_returns_fn(price_df, **params)` grid-test
calling contract for true multi-leg pairs strategies: correlation between
two DIFFERENT underlying assets can't be cleanly computed from a single
already-ratio'd price series without a second raw price input, which this
strategy file's proxy approach only approximates poorly. A future iteration
revisiting this idea should extend the grid-test harness to pass a
secondary raw-price companion series for true cross-asset correlation
computation, rather than reusing this ratio-only proxy.
