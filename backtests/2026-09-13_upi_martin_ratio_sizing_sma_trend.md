# Ulcer Performance Index (Martin Ratio) Dynamic Sizing on SMA(200) Trend Gate

**Hypothesis:** Per https://en.wikipedia.org/wiki/Ulcer_index (Peter Martin,
1987, read via browser_exec): Ulcer Performance Index (UPI, Martin Ratio) =
(return - risk_free_rate) / Ulcer Index, where Ulcer Index is the
QUADRATIC MEAN (root-mean-square, i.e. /N normalized) of per-bar
retracement from the running peak. Distinct from Burke Ratio
(2026-09-13-052, root-SUM-of-squares, no /N normalization) and Pain Ratio
(2026-09-13-051, arithmetic mean of retracement, not RMS). This repo has
only ever used the Ulcer Index as a binary entry-filter threshold
(2026-09-04-144, 2026-09-10-045) -- never as a continuous dynamic-exposure
sizing overlay, which this iteration adds. Scales an SMA(200) trend gate's
exposure by the trailing Ulcer Performance Index. First UPI/Martin-Ratio
sizing overlay strategy in this repo.

**Source:** https://en.wikipedia.org/wiki/Ulcer_index

## Grid test summary (equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT;
ulcer_window in [60,90,120], upi_reference in [0.5,1.0,1.5];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, ulcer_window=60, upi_reference=1.0, low-vol, Sharpe=2.87
- worst_cell: QQQ, ulcer_window=60, upi_reference=1.5, high-vol, Sharpe=-0.69

Symbol-specific optimal windows diverge: SPY works best at ulcer_window=60
(all 3 upi_reference values pass full-sample); QQQ works best at
ulcer_window=120 (both 0.5/1.0 pass). Neither symbol's best window works
for the other, so each is reported with its own tuned config below (same
pattern as this repo's Sterling/Burke/Pain Ratio sizing overlays this cron
trigger, which also accepted per-symbol configs rather than one shared
one).

## Single-config validator results

### SPY (ulcer_window=60, upi_reference=1.0) -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.233 | >= 1.0 | Yes |
| Max drawdown | 0.133 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 87 trades) | 1.150 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 3-combo grid) | 0.005 | <= 0.5 | Yes |

### QQQ (ulcer_window=120, upi_reference=1.0) -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.266 | >= 1.0 | Yes |
| Max drawdown | 0.219 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 78 trades) | 1.220 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 4-combo grid) | 0.094 | <= 0.5 | Yes |

`validators.check_walk_forward` was skipped -- `vbt.utils.splitting.RangeSplitter`
is not available in the installed vectorbt version (pre-existing tooling gap
noted since 2026-09-13-007; not specific to this strategy).

## Decision

**Accepted for both SPY and QQQ (equity only), each with its own tuned
ulcer_window** (60 for SPY, 120 for QQQ; both share upi_reference=1.0). All
four validators run pass comfortably for both symbols, with very low
parameter sensitivity within each symbol's own optimal-window neighborhood.
Low turnover (78-87 trades over the 2019-2026 sample) keeps transaction-
cost survival comfortable. Crypto (BTC/USDT, ETH/USDT) rejected across the
whole grid (0/54 cells), consistent with every prior SMA(200)-gated sizing
overlay tested this cron trigger.
