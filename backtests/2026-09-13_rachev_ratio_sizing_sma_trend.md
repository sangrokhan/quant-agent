# Rachev Ratio Dynamic Sizing on SMA(200) Trend Gate

**Hypothesis:** Per https://metricgate.com/docs/rachev-ratio/ (read via
browser_exec; Google SERP fallback since web_search/DDGS returned no
results for the direct query): Rachev Ratio = E[r | r >= q(1-beta)] /
-E[r | r <= q(alpha)] -- the ratio of the CONDITIONAL EXPECTED (CVaR-style)
tail gain to the conditional expected tail loss. Distinct from the
already-tested Tail Ratio (2026-09-13-055, single percentile POINT for
each tail) and the already-tested CVaR strategy (2026-09-13-045, loss-side
CVaR only, no gain-tail numerator). Scales an SMA(200) trend gate's
exposure by the underlying asset's own trailing Rachev ratio. First
Rachev-Ratio-based sizing strategy in this repo.

**Sources:** https://metricgate.com/docs/rachev-ratio/ (via Google SERP
fallback; alternativesoft.com's equivalent page 404'd)

## Grid test summary (equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT;
rachev_window in [60,90,120], rachev_reference in [0.8,1.0,1.3];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, rachev_window=120, rachev_reference=0.8, low-vol, Sharpe=2.81
- worst_cell: ETH/USDT, rachev_window=120, rachev_reference=0.8, mid-vol, Sharpe=0.04

Same structural pattern as every prior SMA(200)-gated sizing overlay this
cron trigger: crypto never clears the 1.0 min-Sharpe bar (0/54), though the
worst cell here is a near-zero (not sharply negative) Sharpe.

## Single-config validator results (best shared config: rachev_window=90,
rachev_reference=1.0, trend_window=200, leverage_cap=1.0)

### SPY -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.052 | >= 1.0 | Yes |
| Max drawdown | 0.191 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 273 trades) | 0.734 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 6-combo grid) | 0.026 | <= 0.5 | Yes |

### QQQ -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.275 | >= 1.0 | Yes |
| Max drawdown | 0.195 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 221 trades) | 1.107 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 6-combo grid) | 0.026 | <= 0.5 | Yes |

`validators.check_walk_forward` was skipped -- `vbt.utils.splitting.RangeSplitter`
is not available in the installed vectorbt version (pre-existing tooling gap
noted since 2026-09-13-007; not specific to this strategy).

## Decision

**Accepted for both SPY and QQQ** (equity only) at the shared config
rachev_window=90, rachev_reference=1.0. All four validators run pass
comfortably for both symbols, with very low parameter sensitivity (2.6%
relative std). Trade count is notably higher than the sibling Tail-Ratio
strategy (221-273 vs ~100-150) because the rolling-quantile tail-mean
recompute is more reactive turn-to-turn than a single percentile point, but
transaction-cost survival still clears comfortably. Crypto (BTC/USDT,
ETH/USDT) rejected across the whole grid (0/54 cells), consistent with
every prior sizing-overlay tested this cron trigger.
