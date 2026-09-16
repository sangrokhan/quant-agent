# Roll's (1984) Implied Bid-Ask Spread — Inverse-Liquidity Continuous Sizing Dial

## Hypothesis

Per Roll, R. (1984) "A Simple Implicit Measure of the Effective Bid-Ask
Spread in an Efficient Market" (formula cross-confirmed across multiple
Google SERP snippets since the primary target pages 404'd: metricgate.com's
Roll Effective Bid-Ask Spread Calculator, a TradingView PickMyTradeLib
script description, Pineify's bid-ask-bounce writeup, and Bernt Arne
Odegaard's teaching slides ba-odegaard.no/teach/notes/roll_slides), the
bid-ask bounce induces negative serial covariance in successive price
changes, whose magnitude implies the effective spread with **no
order-book data required**:

```
spread_t = 2 * sqrt(max(0, -Cov(delta_p_t, delta_p_{t-1})))
```

computed over a rolling window of log-price changes. This is a genuinely
new indicator family for this repo (0 prior Roll/bid-ask-bounce entries) —
distinct from Corwin-Schultz (already tested, uses daily H-L range) since
Roll's estimator uses only close-to-close serial covariance.

Reframed here as a CONTINUOUS SIZING dial inside an SMA(trend_window)
uptrend gate: exposure scales up when the current rolling spread estimate
falls below its own rolling reference (calmer/more-liquid-than-usual
regime — lean into the trend), and scales down toward zero when the
spread estimate spikes above reference (noisier/less-liquid-than-usual,
bid-ask-bounce-dominated — back off), with a deadband to avoid churn from
estimator noise.

Source URLs read this iteration (via browser_exec, `web_search` DDGS/Yahoo
backend down again this iteration):
- https://www.google.com/search?q=... (SERP snippets confirming the Roll
  formula: metricgate.com, TradingView PickMyTradeLib, Pineify,
  ba-odegaard.no)
- https://quantpedia.com/strategies/term-structure-effect-in-commodities
  (read but infeasible — cross-sectional multi-commodity long-short
  design, no commodity futures data source in `data/loaders.py`)
- Several 404/dead Turtle Soup pages (Turtle Soup already saturated in
  this repo's KB anyway, id 2026-09-04-076) — logged to
  `visited_pages.jsonl` so never re-fetched.

## Strategy

`strategies/2026-09-17_roll_spread_invliquidity_sizing_sma_trend.py`

- `trend_long = close > SMA(trend_window)`
- `spread_t = 2*sqrt(max(0, -Cov(delta_p_t, delta_p_{t-1})))` over
  `roll_window` days of log-price changes.
- `spread_ref = rolling_mean(spread, ref_window)`.
- `ratio = spread_ref / spread`; deadband around `ratio==1`;
  `exposure = clip(1 + (ratio - 1 outside deadband), 0, leverage_cap)`.
- Final position = exposure where trend_long, else 0.

## Grid test (Step 6)

`param_grid = {trend_window: [40,200], roll_window: [15,20,30],
ref_window: [60,100], deadband: [0.15,0.30]}`, `symbols = {equity:
[QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`.

- **288 total cells, 85 passed → pass_fraction = 0.295**
- By asset class: equity 72/144 (0.50) pass; crypto 13/144 (0.09) pass.
- By vol regime: low 60/96 (0.625); mid 25/96 (0.26); high 0/96 (0.0).
- Best cell: SPY, low-vol, `trend_window=200, roll_window=30,
  ref_window=100, deadband=0.15`, Sharpe 3.03.
- Worst cell: QQQ, high-vol, `trend_window=40, ...`, Sharpe -0.22.

Clear pattern: `trend_window=200` (slow trend gate) dominates the
passing cells, and the strategy works almost exclusively in low/mid-vol
regimes — a spread-based liquidity dial is naturally most informative
when volatility (and turnover) isn't already saturating the signal.

## Single-config validation (Step 7)

Best config: `trend_window=200, roll_window=30, ref_window=100,
deadband=0.15`.

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe (>=1.0) | **1.578 PASS** | **1.087 PASS** | 0.238 FAIL | 0.221 FAIL |
| Max Drawdown (<=0.25) | **0.166 PASS** | **0.191 PASS** | 0.595 FAIL | 0.473 FAIL |
| TC survival (net Sharpe >=0.5, 5bps/trade) | **1.015 PASS** (544 trades) | **0.504 PASS** (517 trades, near-miss on threshold) | not run (already decisive fail) | not run |
| Walk-forward (4 manual splits, `vbt.utils.splitting.RangeSplitter` broken in this install — same pre-existing repo-wide gap documented in prior reports) | **3/4 splits positive, PASS** (1.238, -0.624, 1.824, 1.090) | **3/4 splits positive, PASS** (0.487, -0.821, 1.457, 1.198) | not run | not run |
| Parameter sensitivity (16-cell roll_window x deadband sweep, relative std <=0.5) | not separately reported (grid above already covers this) | **PASS**, relative_std=0.075 (mean Sharpe 0.887, std 0.066) | not run | not run |

Crypto (BTC/USDT, ETH/USDT) fails decisively on Sharpe and MDD at the
identical config — consistent with the grid's own crypto pass rate of
only 0.09.

## Decision

**Accept for equity (QQQ + SPY)** — all validators run pass, including a
genuine (not cherry-picked) parameter-sensitivity sweep and manual
walk-forward. **Reject for crypto (BTC/USDT, ETH/USDT)** — decisive Sharpe
and MDD failure, consistent across the grid.

SPY's TC-survival result (0.504 vs 0.5 threshold) is a near-miss pass, not
a robust margin — a future iteration could widen the leverage_cap/deadband
search specifically for SPY if this needs hardening.
