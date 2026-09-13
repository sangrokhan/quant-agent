# CCI (Commodity Channel Index) Continuous Sizing Overlay on SMA(200) Trend Gate

**Hypothesis:** Per Google SERP synthesis (Investopedia/Wikipedia/Fidelity,
browser_exec): CCI = (TypicalPrice - SMA(TypicalPrice)) / (0.015 *
MeanDeviation), TypicalPrice=(H+L+C)/3. This repo has 13+ prior CCI
entries, all binary threshold/crossover entries. This iteration uses CCI
as a CONTINUOUS SIZING dial on the SMA(200) trend gate: exposure =
clip(cci / cci_reference, 0, leverage_cap). First CCI-as-continuous-sizing
strategy in this repo.

**Source:** https://www.google.com/search?q=Commodity+Channel+Index+CCI+formula+typical+price+mean+deviation

## Grid test summary (equity: SPY/QQQ, crypto: BTC/USDT/ETH/USDT;
cci_window in [14,20,30], cci_reference in [100.0,150.0,200.0];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 25, pass_fraction: 0.231
- by_asset_class: equity 25/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 7/36, high 0/36
- best_cell: QQQ, cci_window=30, cci_reference=100.0, low-vol, Sharpe=2.595
- worst_cell: QQQ, cci_window=30, cci_reference=200.0, high-vol, Sharpe=-0.381

## Full-sample best-config search (wider secondary sweep: cci_window in
[10,14,20,30,40], cci_reference in [80,100,150,200,250])

| Symbol | Best config | Full-sample Sharpe |
|---|---|---|
| SPY | cci_window=14, cci_reference=200.0 | 0.855 |
| QQQ | cci_window=40, cci_reference=80.0 | 0.965 |

Both symbols' best full-sample Sharpe across a 25-combination secondary
sweep remain below the 1.0 threshold. Given neither symbol clears the bar
even at its individually-optimized best config, the full single-config
validator suite (MDD/txn-cost/walk-forward/param-sensitivity) was not run
-- the decisive Sharpe shortfall makes it moot (consistent with this
repo's convention for clearly-failing grid results, e.g. the Treynor-Ratio
and Kelly-Criterion entries).

## Decision

**Rejected (both SPY and QQQ, decisively).** No parameter combination
across a 9-cell primary grid or a 25-cell secondary sweep reaches the 1.0
full-sample Sharpe bar (best: QQQ 0.965). CCI's unbounded, noisier scale
(unlike Aroon's naturally bounded [-100,100] recency measure, or %B's
naturally bounded [0,1] price-position measure, both accepted this cron
trigger) appears to make it a less reliable continuous sizing dial --
CCI's magnitude is driven by the mean-absolute-deviation normalization,
which can produce erratic large swings unrelated to genuine trend
strength. Crypto (BTC/USDT, ETH/USDT) rejected decisively across the whole
grid (0/54 cells), consistent with nearly every strategy tested this cron
trigger.
