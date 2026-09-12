# 2026-09-13 Zakamulin Duration-Dependent Momentum — Backtest Report

**Hypothesis:** Per Zakamulin & Giner's "Optimal Trend Following Rules in
Two-State Regime-Switching Models" (summarized at
https://allocatesmartly.com/zakamulins-optimal-trend-following/, read via
browser_exec this iteration — alphaarchitect.com's own page is
Cloudflare-blocked and web_extract's ddgs backend cannot fetch page
content), the theoretically-optimal trend-following indicator (fit via a
semi-Markov switching model to 124 years of market data) weights recent
monthly returns (lag <= ~8 months) POSITIVELY and intermediate-lag returns
(lag ~10-30 months) NEGATIVELY — "duration dependence": the longer a
regime has persisted, the more likely it is to end. Approximated here as a
two-term indicator: `mean(monthly_ret[1..short_lag]) -
mean(monthly_ret[short_lag+1..long_lag])`, decided/held monthly per the
source's own disclosed rule (evaluate at month-end close, hold the
resulting long/cash decision through the following month).

First strategy in this repo combining short-term momentum POSITIVELY with
intermediate-term momentum NEGATIVELY in one duration-dependent signal.

## Single-config validators (full sample 2000-01-01 to 2026-09-01)

| Symbol | Config | Sharpe | MDD | Trades | Net Sharpe (10bps/trade) |
|---|---|---|---|---|---|
| SPY | short=10/long=30 | 0.694 (FAIL) | 0.341 (FAIL) | 44 | 0.675 (FAIL) |
| SPY | short=8/long=24 (source's approx description) | 0.554 (FAIL) | 0.341 (FAIL) | 44 | 0.535 (FAIL) |
| QQQ | short=10/long=30 | 0.772 (FAIL) | 0.342 (FAIL) | 37 | 0.759 (FAIL) |
| QQQ | short=8/long=24 | 0.608 (FAIL) | 0.492 (FAIL) | 51 | 0.591 (FAIL) |

All full-sample Sharpe/MDD/TC-survival configs fail decisively. Walk-forward
and parameter-sensitivity skipped (already decisively rejected on the first
three validators; also `validators.check_walk_forward` errors in this
environment — `vbt.utils.splitting.RangeSplitter` not present in the
installed vectorbt version, a pre-existing tooling gap noted previously in
2026-09-13-007's report).

## Step 6 grid summary (short_lag_months in [6,8,10] x long_lag_months in [18,24,30], SPY/QQQ + BTC/USDT/ETH/USDT, vol_regime_splits=3, window 2016-01-01 to 2026-09-01)

- 108 total cells, 24 passed (pass_fraction 0.222)
- **by_asset_class**: equity 24/54 (44%), crypto 0/54 (0%)
- **by_vol_regime**: low 16/36 (44%), mid 8/36 (22%), high 0/36 (0%)
- Best cell: short_lag_months=10, long_lag_months=30, SPY, low-vol regime, Sharpe 1.953
- Worst cell: short_lag_months=6, long_lag_months=30, ETH/USDT, mid-vol regime, Sharpe 0.025

## Decision: REJECTED

The 2016-2026 grid window (which excludes the 2008 GFC) shows a real edge
concentrated in equity/low-vol cells, but the full 2000-2026 sample (which
includes 2008 and the 2020 COVID crash) shows full-sample Sharpe well
below 1.0 and max drawdown ~34% on both SPY and QQQ — the monthly-decide
mechanism reacts too slowly (holding a losing position for up to a full
month) to avoid the deep 2008/2020 drawdowns, consistent with
AllocateSmartly's own finding that the Optimal Strategy's edge "has ebbed
over time" and "provided essentially no added benefit since [the
mid-2000s]" relative to simpler trend-following rules. Crypto is decisively
rejected across the entire grid (0/54) — monthly-decision cadence is too
slow for BTC/ETH's volatility profile.

## Notes for future iterations

- This is a genuine, real finding distinct from prior work: the source's
  own qualitative "duration dependence ebbed over time" caveat is directly
  corroborated by this repo's own full-sample vs. recent-window grid
  discrepancy (44% pass in the 2016+ window vs. decisive full-sample
  failure once 2008/2020 are included).
- A DAILY re-evaluation (rather than monthly-decide/hold) variant might
  react faster to drawdowns while keeping the duration-dependent weighting
  concept — worth a follow-up iteration, though it would move further from
  the source's own disclosed monthly-cadence rule.
- The exact SMSM-fitted weight curve is not numerically disclosed by the
  source (only shown as a chart) — this test uses a simplified two-term
  step-function approximation (positive weight on lags 1..short_lag,
  negative on short_lag+1..long_lag) rather than the true continuous
  weighting; a more faithful replication was not possible without the
  paper's exact coefficients (SSRN/Springer paper not directly accessed
  this iteration).
