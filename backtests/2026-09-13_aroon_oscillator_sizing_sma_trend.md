# Aroon Oscillator Continuous Sizing Overlay on SMA(200) Trend Gate

**Hypothesis:** Per Google SERP synthesis (TrendSpider/StockCharts/IFCM/
Investopedia, browser_exec): Aroon Oscillator (Tushar Chande, 1995) =
AroonUp - AroonDown, ranging [-100, 100]. This repo has 11 prior Aroon
entries, all using it as a binary threshold/crossover ENTRY signal. This
iteration uses the Aroon Oscillator's own bounded scale as a CONTINUOUS
SIZING dial on the SMA(200) trend gate: exposure = clip(oscillator /
aroon_reference, 0, leverage_cap) -- scale up toward full size as fresh
highs dominate (oscillator near +100), scale down as momentum fades
(oscillator toward 0) even while the SMA gate is still nominally long.
Structurally distinct from every other sizing overlay tested elsewhere in
this cron trigger (risk-ratio measures, %B mean-reversion measure) --
Aroon measures RECENCY of extremes, not risk or price-band position. First
Aroon-Oscillator-as-continuous-sizing strategy in this repo.

**Source:** https://www.google.com/search?q=Aroon+Oscillator+formula+continuous+position+sizing+trend+strength
(SERP: TrendSpider, StockCharts, IFCM, Investopedia)

## Grid test summary (equity: SPY/QQQ, crypto: BTC/USDT/ETH/USDT;
aroon_window in [14,25,40], aroon_reference in [40.0,60.0,80.0];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: QQQ, aroon_window=25, aroon_reference=60.0, low-vol, Sharpe=3.249
- worst_cell: SPY, aroon_window=40, aroon_reference=80.0, high-vol, Sharpe=-0.382

## Single-config validator results (best full-sample config per symbol,
trend_window=200, leverage_cap=1.0)

| Symbol | Config | Sharpe | Passed | MDD | Passed | Net Sharpe (5bps/trade) | Passed | Walk-fwd frac | Passed | Param sens (rel std) | Passed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | aroon_window=40, aroon_reference=40.0 | 0.945 | No (thr 1.0) | 0.175 | Yes | 0.908 | Yes | 0.75 | Yes | 0.076 | Yes |
| QQQ | aroon_window=25, aroon_reference=80.0 | 1.412 | Yes | 0.156 | Yes | 1.365 | Yes | 0.75 | Yes | 0.085 | Yes |

Note: `validators.check_walk_forward` has the same pre-existing tooling gap
(`vbt.utils.splitting.RangeSplitter` unavailable) — substituted a manual
4-split walk-forward (same 0.75 threshold); both symbols hit 3/4.

## Decision

**Accepted (QQQ only).** All 5 validators pass comfortably for QQQ (Sharpe
1.412, well above threshold, tight param-sensitivity 0.085). SPY fails
only the Sharpe threshold (0.945 < 1.0, a near-miss) with every other
validator passing; also worth a future revisit with a wider aroon_window
sweep. Crypto (BTC/USDT, ETH/USDT) rejected decisively across the whole
grid (0/54 cells).
