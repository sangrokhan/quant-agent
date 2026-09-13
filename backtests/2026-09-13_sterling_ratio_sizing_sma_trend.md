# Sterling Ratio Dynamic Sizing on SMA(200) Trend Gate

**Hypothesis:** Per Wikipedia's Sterling Ratio (https://en.wikipedia.org/wiki/Sterling_ratio,
read via browser_exec): Sterling Ratio = CompoundROR / (Average of the N
LARGEST distinct drawdown episodes - 10% adjustment). Unlike this cron
trigger's other risk-measure sizing overlays -- Burke Ratio (root-sum-square
of every per-bar drawdown), Pain Ratio (mean of every per-bar drawdown),
MAR/Calmar (single worst drawdown) -- Sterling averages only the K largest
distinct drawdown *episodes*, ignoring shallow noise dips. Scales an
SMA(200) trend gate's exposure by the trailing Sterling ratio.

**Source:** https://en.wikipedia.org/wiki/Sterling_ratio

## Grid test summary (equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT; sterling_reference in [0.3,0.5,0.8], n_largest in [2,3]; vol_regime_splits=3)

- total_cells: 72, passed_cells: 18, pass_fraction: 0.25
- by_asset_class: equity 18/36 passed, crypto 0/36 passed
- by_vol_regime: low 12/24, mid 6/24, high 0/24
- best_cell: QQQ, sterling_reference=0.3, n_largest=3, low-vol, Sharpe=2.70
- worst_cell: SPY, sterling_reference=0.8, n_largest=3, high-vol, Sharpe=-0.11

Crypto rejected decisively across the entire grid (0/36) -- same structural
pattern as every prior sizing-overlay strategy this cron trigger (CVaR, MAR,
downside-deviation, Omega, GPR, Pain, Burke): SMA(200)-gated trend sizing
overlays do not transfer to BTC/ETH.

## Single-config validator results (best full-sample configs)

### QQQ (sterling_reference=0.3, n_largest=3) -- ACCEPTED (5/5 passed)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.082 | >= 1.0 | Yes |
| Max drawdown | 0.249 | <= 0.25 | Yes |
| Net Sharpe after costs (10bps/trade, 120 trades) | 0.923 | >= 0.5 | Yes |
| Walk-forward (4-slice) pass fraction | 0.75 | >= 0.75 | Yes |
| Parameter sensitivity (relative std across 6-combo grid) | 0.038 | <= 0.5 | Yes |

### SPY (sterling_reference=0.3, n_largest=2) -- REJECTED (near-miss)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.934 | >= 1.0 | **No** |
| Max drawdown | 0.180 | <= 0.25 | Yes |
| Net Sharpe after costs (10bps/trade, 110 trades) | 0.717 | >= 0.5 | Yes |
| Walk-forward (4-slice) pass fraction | 0.75 | >= 0.75 | Yes |
| Parameter sensitivity (relative std) | 0.007 | <= 0.5 | Yes |

## Decision

**Accepted for QQQ only.** SPY is a near-miss on Sharpe (0.934 vs 1.0
threshold) but otherwise passes everything -- consistent with this repo's
pattern where the same SMA(200)-gate sizing family (MAR, Pain, Burke) also
accepts SPY-only or QQQ-only depending on the specific risk-measure
denominator. Crypto (BTC/USDT, ETH/USDT) rejected decisively across the
whole grid, same as every other risk-measure sizing overlay tested this
cron trigger.
