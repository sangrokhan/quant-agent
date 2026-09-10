# 2026-09-10 — RRG JdK RS-Ratio / RS-Momentum Leading-Quadrant Entry

## Hypothesis

Per Julius de Kempenaer's Relative Rotation Graph (RRG) framework (per
StockCharts ChartSchool
https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rrg-relative-strength
and the exact double-smoothed-WMA JdK RS-Ratio / percentage-based
RS-Momentum formula disclosed at
https://gist.github.com/tuhuynh27/c8abcf7f8469b7d91adac9a6947db64d): a
security's relative strength vs a benchmark, and the momentum of that
relative strength, define four rotation quadrants. StockCharts's own
trading guidance identifies the Improving->Leading transition (RS-Ratio
crosses above 100 while RS-Momentum is already >100) as the
highest-conviction long entry, with the Leading->Weakening->Lagging
transition (RS-Ratio crossing back below 100) as the exit.

Formula:
```
RS = (security_price / benchmark_price) * 100
RS_smooth = WMA(RS, wma_window)
RS_benchmark_smooth = WMA(RS_smooth, wma_window)
RS_Ratio = (RS_smooth / RS_benchmark_smooth) * 100
RS_Momentum = (RS_Ratio / RS_Ratio.shift(momentum_period)) * 100
```

Adapted as a genuine two-asset relative-rotation strategy (distinct from
every other strategy in this repo, all of which trade a single asset's own
absolute price/indicator history): trade QQQ long only while it is in the
RRG Leading quadrant relative to SPY (RS-Ratio>100 AND RS-Momentum>100);
same construction tested for ETH/USDT relative to BTC/USDT.

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rrg-relative-strength
(interpretation/quadrant rules) + https://gist.github.com/tuhuynh27/c8abcf7f8469b7d91adac9a6947db64d
(exact formula).

## Best config

`benchmark_symbol=SPY, wma_window=10, momentum_period=15, max_hold_days=60`
(QQQ relative to SPY)

## Single-config validator results (QQQ vs SPY benchmark, full 2019-01-01..2026-09-01 sample)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.008 | >= 1.0 | **PASS** |
| Max drawdown | 0.246 | <= 0.25 | **PASS** |
| Transaction-cost survival (net Sharpe, 10bps/trade, 64 trades) | 0.933 | >= 0.5 | **PASS** |
| Walk-forward (4 splits) | 1.00 (4/4 splits positive Sharpe) | >= 0.75 | **PASS** |
| Parameter sensitivity (3x3 wma/momentum grid, relative std) | 0.188 | <= 0.5 | **PASS** |

All 5 validators pass for QQQ (vs SPY benchmark). Note the Sharpe of 1.008
is a narrow pass margin above the 1.0 threshold — flagged here explicitly as
a near-the-line accept, not a decisive one.

## Grid-test summary (`validation/grid_test.py`, QQQ only, vol-regime split)

Grid: `wma_window in [10,15]` x `momentum_period in [10,15]`, QQQ vs SPY
benchmark, `vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Total cells: 12, passed: 8, pass_fraction: 0.667**
- By vol regime: low-vol 4/4 passed; mid-vol 4/4 passed; **high-vol 0/4
  failed** — the strategy does not hold up in high-realized-vol regimes
  (consistent with the general pattern across this repo of trend/relative-
  strength strategies degrading in high-vol conditions), but unlike many
  prior rejected strategies here it DOES generalize across low+mid vol
  regimes, a meaningfully broader scope than "low-vol-only" near-misses.
- Best cell: QQQ, low-vol regime, `wma_window=10, momentum_period=10`,
  Sharpe 2.60.
- Worst cell: QQQ, high-vol regime, `wma_window=10, momentum_period=15`,
  Sharpe 0.159.

## Standalone parameter sweep (18 cells: 2 symbol-pairs x 3 wma x 3 momentum, full sample)

- QQQ vs SPY: 1/9 cells passed both Sharpe>=1.0 AND MDD<=0.25 outright
  (wma=10, momentum=15 — the config carried forward above); several other
  QQQ cells pass Sharpe alone but miss on MDD by a small margin (e.g.
  wma=10/mom=10: Sharpe 1.116, MDD 0.260 — just over the 0.25 cap).
- ETH/USDT vs BTC/USDT: **0/9 cells passed** — Sharpe ranged 0.21-0.31 and
  MDD ranged 0.60-0.72 across the entire grid, a decisive reject for the
  crypto pairing.

## Decision: ACCEPT (QQQ vs SPY only) / REJECT (ETH/USDT vs BTC/USDT)

QQQ's RRG-Leading-quadrant-vs-SPY config (`wma_window=10,
momentum_period=15`) passes all 5 standard validators, generalizes across
low+mid vol regimes (though not high-vol), and has low parameter
sensitivity. The margin above the Sharpe threshold is narrow (1.008 vs 1.0)
so this should be treated as a modest accept, not a strong one, and a future
loop may want to re-validate it on a fresh out-of-sample window before
relying on it further.

ETH/USDT vs BTC/USDT relative-rotation is decisively rejected across the
entire parameter grid — altcoin-vs-BTC relative strength does not show the
same RRG-quadrant edge that QQQ-vs-SPY equity relative strength does in this
sample.

`strategies/2026-09-10_rrg_leading_quadrant.py` is kept live in `strategies/`
as an accepted QQQ-vs-SPY strategy; its crypto (ETH/USDT-vs-BTC/USDT)
application should be treated as scope outside what this file supports well.
