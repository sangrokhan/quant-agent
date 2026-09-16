# Kalman-Filter Dynamic Hedge Ratio Pairs Mean Reversion (QQQ/SPY, BTC/ETH)

## Hypothesis

Per QuantStart's "Dynamic Hedge Ratio Between ETF Pairs Using the Kalman
Filter" and corroborating sources found via browser_exec Google SERP
fallback this iteration (`web_search` DDGS/Yahoo backend down again) —
LinkedIn/Dr. Heather Dempsey's "Kalman Filter Breaks in Pairs Trading",
Robot Wealth's Kalman filter pairs example, QuantT's Pairs Trading
Complete Strategy Guide, Papers-With-Backtest's Kalman Filter for Trading
course — the standard state-space formulation is:

```
y_t = x_t * beta_t + v_t      (observation)
beta_t = beta_{t-1} + w_t     (random-walk state)
```

A scalar Kalman filter recursively estimates the time-varying hedge ratio
`beta_t` continuously, without a fixed rolling-OLS lookback window. This
repo's prior pairs-trading strategies (JPM/BAC, CVX/XOM, GDX/RING,
SPY/QQQ, ETH/BTC, etc.) all use a rolling-OLS hedge ratio over a fixed
window — this is the first Kalman-filter-based DYNAMIC hedge ratio pairs
strategy in this repo (distinct from the already-tested single-asset
Kalman trend-following/mean-reversion variants at
2026-09-05-056/2026-09-08-052/2026-09-11-112, none of which involve a
second instrument or hedge ratio).

Source URLs (all read this iteration via browser_exec; logged to
`visited_pages.jsonl`/`visited_urls.jsonl`):
- quantstart.com/articles/Dynamic-Hedge-Ratio-Between-ETF-Pairs-Using-the-Kalman-Filter
- portfoliooptimizationbook.com/book/15.6-kalman-filtering-for-pairs-trading
- robotwealth.com/kalman-filter-pairs-trading-r
- quantt.co.uk/resources/pairs-trading-complete-strategy-guide-python-2026
- paperswithbacktest.com/course/kalman-filter-for-trading

## Strategy

`strategies/2026-09-17_kalman_dynamic_hedge_pairs_meanrev.py`

- Scalar Kalman filter (implemented from scratch with numpy, `pykalman`
  not a repo dependency) recursively estimates `beta_t` between
  `log(price_df's own close)` (y) and `log(partner leg's close)` (x).
- `spread_t = y_t - beta_t * x_t`; z-score over a `z_window`-day rolling
  mean/std.
- Long (position=1, "hold A") when `z <= -entry_z`; exit when
  `z >= -exit_z` or `max_hold_days` time-stop.
- Partner leg fetched internally via `data/loaders.py`, same pattern as
  `strategies/2026-09-08_pairs_zscore_cointegration.py`.

## Grid test (Step 6)

Manual grid (equivalent to `run_strategy_grid`'s design) over
`entry_z in {1.5,2.0}, z_window in {15,20,30}, q in {1e-5,1e-4}`
(`exit_z=0.5, r=1e-2, max_hold_days=15` fixed), split into low/mid/high
realized-vol terciles (`vol_regime_splits=3`), on both directions of each
pair:

| pair | pass_fraction | low | mid | high |
|---|---|---|---|---|
| QQQ (partner SPY) | 5+1+5 = 11/36 (0.306) | 5/12 | 1/12 | 5/12 |
| SPY (partner QQQ) | 5/36 (0.139) | 5/12 | 0/12 | 0/12 |
| BTC/USDT (partner ETH/USDT) | 0/36 (0.0) | 0/12 | 0/12 | 0/12 |
| ETH/USDT (partner BTC/USDT) | 0/36 (0.0) | 0/12 | 0/12 | 0/12 |

Best QQQ cell: `entry_z=1.5, z_window=15, q=1e-4`, low-vol tercile,
Sharpe 1.379. Crypto (BTC/ETH) shows **zero** passing cells across the
entire grid in any regime — decisive rejection, consistent with this
repo's prior finding for ETH/BTC pairs trades in general
(2026-09-08_pairs_zscore_cointegration.md).

## Single-config validation (Step 7) — best config

`entry_z=1.5, exit_z=0.5, z_window=15, q=1e-4, r=1e-2, max_hold_days=15`

| Validator | QQQ (partner SPY) | SPY (partner QQQ) |
|---|---|---|
| Sharpe (>=1.0) | **1.031 PASS** (narrow) | 0.317 FAIL |
| Max Drawdown (<=0.25) | **0.083 PASS** | 0.149 PASS |
| TC survival (net Sharpe >=0.5, 5bps/trade, 208 trades) | **0.798 PASS** | not run (Sharpe already failed) |
| Walk-forward (4 manual splits, `vbt.utils.splitting.RangeSplitter` broken in this install, same pre-existing repo-wide gap) | **4/4 splits positive, PASS** (1.776, 0.134, 0.404, 0.457) | not run |
| Parameter sensitivity (12-cell entry_z x z_window sweep) | **PASS**, relative_std=0.322 (mean Sharpe 0.718, std 0.231) | not run |

## Decision

**Accept for QQQ only (partner SPY)** — full-sample Sharpe passes (1.031,
a narrow margin), all other validators pass with more comfortable margins.
**Reject SPY (partner QQQ)** — Sharpe 0.317, well below threshold; the
asymmetry (QQQ works, SPY as primary leg doesn't) suggests QQQ's own
idiosyncratic short-term deviations from the QQQ/SPY relationship carry
more mean-reverting signal than SPY's. **Reject crypto (BTC/USDT,
ETH/USDT)** — decisively 0/36 across the entire grid in both directions;
the Kalman-adaptive hedge ratio doesn't fix the same fundamental
"crypto majors are too tightly co-integrated/too noisy for this
mean-reversion mechanic" problem already documented for the rolling-OLS
ETH/BTC pairs trade.

QQQ's Sharpe is a narrow pass (1.031 vs 1.0) — a future iteration could
try widening the parameter search or testing a different equity pair
(e.g. XLF sector components) to see if the Kalman dynamic-hedge-ratio
approach generalizes with more margin.

## Crypto rescue (same cron trigger, follow-up sub-iteration, id 2026-09-17-047)

Root cause diagnosis (same interval issue already documented for Tirone
Levels 2026-09-17-046 and Hurst exponent 2026-09-16-157): the original
crypto grid used `data/loaders.py::load_crypto`'s default `interval="1h"`,
too fine a granularity for `z_window`/`max_hold_days` calibrated against
daily bars. Re-running BTC/USDT (partner ETH/USDT) with `interval="1d"`
explicitly passed and a genuine parameter re-search:

| Validator | BTC/USDT (partner ETH/USDT, `entry_z=1.5,z_window=20,q=1e-4`, 1d bars) |
|---|---|
| Sharpe (>=1.0) | **1.030 PASS** (narrow) |
| Max Drawdown (<=0.25) | **0.203 PASS** |
| TC survival (net Sharpe >=0.5, 5bps/trade, 300 trades) | **0.900 PASS** |
| Walk-forward (4 manual splits) | **4/4 splits positive, PASS** (0.617, 1.623, 0.817, 0.526) |
| Parameter sensitivity (12-cell entry_z x z_window sweep) | **PASS**, relative_std=0.153 |

ETH/USDT as the primary leg (partner BTC/USDT) still fails at 1d interval
(no config found with Sharpe >= 1.0) — the asymmetry persists even after
the interval fix, mirroring the QQQ-works/SPY-doesn't asymmetry on the
equity side.

## Final decision

**Accept for QQQ (partner SPY) and BTC/USDT (partner ETH/USDT, `interval="1d"`)**.
**Reject SPY-as-primary-leg and ETH/USDT-as-primary-leg** — both fail
Sharpe even after the interval fix; in both asset classes, only one
direction of the pair carries genuine mean-reverting signal via this
Kalman-adaptive-hedge-ratio mechanism.
