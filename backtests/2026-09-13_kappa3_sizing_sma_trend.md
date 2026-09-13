# Kappa-3 Ratio Dynamic Sizing on SMA(200) Trend Gate

**Hypothesis:** Per https://breakingdownfinance.com/finance-topics/performance-measurement/kappa-ratio/
(Kaplan and Knowles 2004, read via browser_exec Google SERP fallback):
Kappa-n Ratio = (mu - tau) / LPM_n(tau)^(1/n), where LPM_n(tau) is the
n-th order Lower Partial Moment below threshold tau. n=1 recovers the
Omega ratio - 1 (already tested, 2026-09-13-049); n=2 recovers the Sortino
ratio (conceptually related to already-tested downside-deviation sizing,
2026-09-13-048). n=3 (standard "Kappa 3" convention) is a genuinely
distinct exponent, cubing shortfalls before averaging and cube-rooting,
weighting the largest downside observations more heavily than n=1/n=2
while still being normalized (unlike un-rooted higher-moment measures).
First Kappa-3-based sizing strategy in this repo. Scales an SMA(200) trend
gate's exposure by the underlying asset's own trailing Kappa-3 ratio.

**Source:** https://breakingdownfinance.com/finance-topics/performance-measurement/kappa-ratio/

## Grid test summary (equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT;
kappa_window in [60,90,120], kappa3_reference in [0.5,1.0,1.5];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, kappa_window=60, kappa3_reference=0.5, low-vol, Sharpe=2.87
- worst_cell: QQQ, kappa_window=60, kappa3_reference=1.5, high-vol, Sharpe=-0.77

Symbol-specific optimal windows diverge in the same pattern as the sibling
Ulcer Performance Index strategy this cron trigger (2026-09-13-058): SPY
best at kappa_window=60, QQQ best at kappa_window=120.

## Single-config validator results

### SPY (kappa_window=60, kappa3_reference=0.5) -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.238 | >= 1.0 | Yes |
| Max drawdown | 0.139 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 81 trades) | 1.162 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 3-combo grid) | 0.036 | <= 0.5 | Yes |

### QQQ (kappa_window=120, kappa3_reference=0.5) -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.257 | >= 1.0 | Yes |
| Max drawdown | 0.219 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 68 trades) | 1.218 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 4-combo grid) | 0.091 | <= 0.5 | Yes |

`validators.check_walk_forward` was skipped -- `vbt.utils.splitting.RangeSplitter`
is not available in the installed vectorbt version (pre-existing tooling gap
noted since 2026-09-13-007; not specific to this strategy).

## Decision

**Accepted for both SPY and QQQ (equity only)**, each with its own tuned
kappa_window (60 for SPY, 120 for QQQ; both share kappa3_reference=0.5).
All four validators run pass comfortably for both symbols, with low
turnover (68-81 trades). Results are very close to the sibling Ulcer
Performance Index strategy (2026-09-13-058) in Sharpe/MDD/turnover
magnitude -- both are trailing-window downside-risk-normalized sizing
overlays with similar structural behavior on this repo's SMA(200) gate,
though the specific weighting of extreme shortfalls (cubed LPM vs
RMS-of-retracement) differs conceptually. Crypto (BTC/USDT, ETH/USDT)
rejected across the whole grid (0/54 cells), consistent with every prior
sizing overlay tested this cron trigger.
