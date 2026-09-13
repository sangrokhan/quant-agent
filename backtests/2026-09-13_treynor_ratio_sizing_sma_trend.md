# Treynor Ratio (CAPM Beta) Dynamic Sizing on SMA(200) Trend Gate

**Hypothesis:** Per https://www.investopedia.com/terms/t/treynorratio.asp
(read via browser_exec): Treynor Ratio = (portfolio_return - risk_free_rate)
/ beta_of_portfolio (Jack Treynor, CAPM co-inventor). Unlike every other
sizing overlay tested this cron trigger (all derived purely from the
asset's own return distribution -- drawdown, percentile, CVaR, or
regression-fit based), Treynor scales excess return by SYSTEMATIC risk
only (beta vs SPY as a fixed benchmark, computed even for the crypto leg as
a falsification test). Scales an SMA(200) trend gate's exposure by the
trailing Treynor ratio. First Treynor-Ratio-based (CAPM-beta) sizing
strategy in this repo.

**Source:** https://www.investopedia.com/terms/t/treynorratio.asp

## Grid test summary (equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT;
treynor_window in [60,90,120], treynor_reference in [0.3,0.5,0.8];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, treynor_window=60, treynor_reference=0.3, low-vol, Sharpe=2.64
- worst_cell: QQQ, treynor_window=60, treynor_reference=0.3, high-vol, Sharpe=-0.89

## Single-config validator results (best full-sample configs across the
sweep, trend_window=200, leverage_cap=1.0)

| Symbol | treynor_window | treynor_reference | Full-sample Sharpe | Passed? | MDD |
|---|---|---|---|---|---|
| SPY | 60 | 0.3 | 0.898 | No | 0.100 |
| SPY | 90 | 0.3 | 0.811 | No | 0.111 |
| SPY | 120 | 0.3 | 0.842 | No | 0.143 |
| QQQ | 120 | 0.3 | 0.895 | No | 0.179 |
| QQQ | 60 | 0.3 | 0.881 | No | 0.165 |
| QQQ | 90 | 0.3 | 0.744 | No | 0.203 |

No parameter combination tested across either symbol clears the 1.0
full-sample Sharpe threshold (best: SPY 0.898). MDD is comfortably passed
everywhere (SPY-beta-vs-itself keeps exposure low/conservative -- SPY's own
beta vs SPY is trivially ~1.0, dampening its sizing signal's variance, while
QQQ's beta vs SPY genuinely varies and still underperforms the drawdown-
and percentile-based overlays already accepted this cron trigger).

`validators.check_walk_forward` was skipped (pre-existing tooling gap,
`vbt.utils.splitting.RangeSplitter` unavailable) -- not run given the
decisive Sharpe rejection makes it moot.

## Decision

**Rejected (both SPY and QQQ, decisively).** No parameter combination
reaches the 1.0 Sharpe bar; the CAPM-beta-based systematic-risk scaling
mechanism underperforms every other sizing-overlay family tested this cron
trigger (Omega/GPR/Pain/Burke/Sterling/Tail-Ratio/Rachev all found at least
one passing config). A plausible explanation: for SPY itself, beta vs its
own return series is close to 1 nearly always, so the Treynor signal
degenerates toward a near-constant scalar and loses most of its
regime-discriminating power; QQQ's beta vs SPY does vary meaningfully but
the resulting sizing series still underperforms full-sample. Crypto
(BTC/USDT, ETH/USDT) rejected decisively across the whole grid (0/54 cells)
as expected -- equity-market beta has little relevance to BTC/ETH
positioning.
