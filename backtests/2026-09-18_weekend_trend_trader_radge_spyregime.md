# 2026-09-18-073: Weekend Trend Trader with SPY-as-Fixed-External-Regime (Second Rescue Attempt)

## Hypothesis

Direct fix attempt for 2026-09-18-072 (Weekend Trend Trader, self-referential
regime filter -- SPY Sharpe 0.696 near-miss). -072's own notes flagged the
self-referential regime substitution as the likely culprit. This iteration
uses SPY itself as a FIXED external market-regime reference for gating
QQQ's entries (QQQ's own new-high/ROC triggers unchanged, but "is the
market up" now checks SPY's own 10-week SMA) -- directly implementing the
source ThinkorSwim code's own `input market = {default SPX, NDX, RUT, DJX}`
parameterization rather than approximating it away.

Source: https://usethinkscript.com/threads/weekend-trend-trader-by-nick-radge-strategy-for-thinkorswim.669/
(same as -072).

## Parameter scan (QQQ primary asset, regime_symbol=SPY fixed;
roc_threshold in [0.15,0.30,0.45] x high_window in [13,20,26] x
init_trail_pct in [0.25,0.40], vol_regime_splits=3, 2018-01-01..2026-09-01)

Best average-across-regimes config for QQQ: roc_threshold=0.15,
high_window=26, init_trail_pct=0.4, avg Sharpe 0.841, pass 1/3 vol regimes
-- essentially unchanged from -072's self-referential-regime QQQ result
(0.837).

## Single-config validation (QQQ, regime_symbol=SPY, roc_threshold=0.15,
high_window=26, init_trail_pct=0.4, 2018-01-01..2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.741 | 1.0 | **fail** |
| Max drawdown | 0.178 | 0.25 | pass |
| Net Sharpe after costs (10bps/trade, 11 trades) | 0.730 | 0.5 | pass |
| Walk-forward (4 splits, manual substitute) | 1.00 (4/4) | 0.75 | pass |
| Parameter sensitivity (relative std, 18-combo grid) | 0.196 | 0.5 | pass |

## Decision

**Rejected -- rescue did not work.** Using SPY as a genuine fixed external
regime reference for QQQ produced essentially the SAME result as -072's
self-referential regime filter (Sharpe 0.741 vs 0.696, still well below the
1.0 threshold; other validators all still pass). This disproves the
hypothesis from -072's own notes that the self-referential regime
substitution was the main cause of the shortfall -- QQQ and SPY are highly
correlated broad-market proxies, so substituting one for the other as the
regime reference barely changes the regime-flag timeseries. The genuine
bottleneck is more likely the RARITY of the compound entry condition itself
(20-week/26-week new high AND regime-up AND ROC>15-30%) rather than which
specific asset serves as the regime proxy -- both attempts produced only
7-11 trades over 8.7 years, an inherently underpowered sample regardless of
regime-reference choice. This line of the Weekend Trend Trader adaptation
is now considered exhausted for this repo's single-symbol architecture;
future revisits should target the entry-condition RARITY directly (e.g.
relaxing the ROC threshold much further below 15%, or replacing the strict
new-high requirement with a percentile-based "near-high" condition) rather
than further regime-reference substitutions.
