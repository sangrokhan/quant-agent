# K-Ratio (Kestner) Dynamic Sizing on SMA(200) Trend Gate

**Hypothesis:** Per Investopedia (https://www.investopedia.com/terms/k/kratio.asp)
and WallStreetMojo (https://www.wallstreetmojo.com/k-ratio/), both read via
browser_exec (quantifiedstrategies.com's page hit a bot-check and was
unreadable, logged as visited-but-unhelpful): Lars Kestner's K-Ratio fits an
OLS regression of the log-cumulative-return curve against time within a
trailing window; K-ratio = slope / (std_err_of_slope * sqrt(n)). Unlike
every other risk-measure sizing overlay tested this cron trigger (Omega,
Gain-to-Pain, Pain Ratio, Burke, Sterling, MAR/Calmar, downside-deviation,
CVaR — all drawdown/distribution-based), K-ratio rewards a smooth,
consistently-trending equity curve via regression fit quality, penalizing
choppiness independent of drawdown depth. Scales an SMA(200) trend gate's
exposure by the trailing K-ratio. First K-Ratio-based strategy (entry or
sizing) in this repo.

**Sources:** https://www.investopedia.com/terms/k/kratio.asp ,
https://www.wallstreetmojo.com/k-ratio/ (quantifiedstrategies.com/k-ratio/
attempted but bot-blocked)

## Grid test summary (equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT;
kratio_window in [60,90,120], k_ratio_reference in [0.3,0.5,0.8];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, kratio_window=60, k_ratio_reference=0.3, low-vol, Sharpe=2.82
- worst_cell: QQQ, kratio_window=60, k_ratio_reference=0.3, high-vol, Sharpe=-0.60

Crypto rejected decisively across the entire grid (0/54) -- same structural
pattern as every prior SMA(200)-gated sizing-overlay strategy this cron
trigger (CVaR, MAR, downside-deviation, Omega, GPR, Pain, Burke, Sterling):
these overlays do not transfer to BTC/ETH.

## Single-config validator results (best full-sample config: kratio_window=60,
k_ratio_reference=0.3, trend_window=200, leverage_cap=1.0)

### SPY -- REJECTED (near-miss)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.880 | >= 1.0 | **No** |
| Max drawdown | 0.174 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 196 trades) | 0.687 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 8-combo grid) | 0.055 | <= 0.5 | Yes |

### QQQ -- REJECTED (near-miss, all windows tested)

| kratio_window | k_ratio_reference | Full-sample Sharpe | MDD | Net Sharpe (5bps) |
|---|---|---|---|---|
| 60 | 0.3 | 0.910 | 0.216 | 0.808 |
| 60 | 0.5 | 0.907 | 0.203 | 0.721 |
| 90 | 0.3 | 0.996 | 0.234 | 0.923 |

`validators.check_walk_forward` was skipped -- `vbt.utils.splitting.RangeSplitter`
is not available in the installed vectorbt version (pre-existing tooling gap
noted since 2026-09-13-007; not specific to this strategy).

## Decision

**Rejected (both SPY and QQQ).** Despite a strong grid pass_fraction in
low-vol regimes (Sharpe up to 2.82 in isolated terciles), full-sample Sharpe
falls just short of the 1.0 threshold for every asset/parameter combination
tested (best: QQQ kratio_window=90 at 0.996 -- the closest near-miss on
record this cron trigger). All other validators (MDD, transaction-cost
survival, parameter sensitivity) pass comfortably, and the regime breakdown
(strong low-vol, weak mid-vol, negative high-vol) mirrors every other
SMA(200)-gated sizing overlay tested this run. The regression-based
"trend-consistency" signal does not by itself lift full-sample Sharpe above
the acceptance bar for this repo's standard trend-gate template. Crypto
(BTC/USDT, ETH/USDT) rejected decisively across the whole grid, consistent
with every prior sizing-overlay strategy this cron trigger.
