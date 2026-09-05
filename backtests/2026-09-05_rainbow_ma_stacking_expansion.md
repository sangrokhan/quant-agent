# Rainbow Moving Average Stacking + Spread-Expansion — Backtest Report

**Hypothesis:** Rainbow Moving Average (recursive cascade of N SMAs, each
layer an SMA of the preceding layer) fully bullish-stacked (layer[0] >
layer[1] > ... > layer[N-1]) with the top-minus-bottom spread expanding
signals a strengthening uptrend worth a long entry; exit when the stacking
order breaks or a max_hold_days time-stop.

**Source:** https://www.quantifiedstrategies.com/rainbow-moving-average/
("When the early layer (shorter-period) MAs stay above the subsequent layer
MAs and keep rising further away from the latter, the market is in an
uptrend... The farther away the primary SMA is from the last ones, the
stronger the trend." Page has no published numeric backtest rule -- this
hypothesis mechanically operationalizes that qualitative description.)

**Strategy file:** `strategies/2026-09-05_rainbow_ma_stacking_expansion.py`

## Step 6 — Grid test summary (param_grid: window in [3,5,8] x n_layers in
[6,8,10]; symbols: equity QQQ/SPY, crypto BTC/USDT, ETH/USDT;
vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 108, passed_cells: 14, **pass_fraction: 0.130**
- by_asset_class: equity 14/54 (26%), crypto 0/54 (0%, decisive fail)
- by_vol_regime: low 14/36 (39%, ALL passes here), mid 0/36, high 0/36
- best_cell: window=3, n_layers=8, QQQ, low-vol, Sharpe=2.105
- worst_cell: window=8, n_layers=10, QQQ, high-vol, Sharpe=-1.327

Same qualitative pattern as several prior "stacking/trend" strategies in
this repo: the edge exists only in the equity low-realized-vol tercile;
crypto is a complete, decisive failure across all 54 cells.

## Step 7 — Single-config validators (best grid config: window=3, n_layers=8,
spread_lookback=20, max_hold_days=20, full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **FAIL** 0.709 | **FAIL** 0.560 |
| Max Drawdown (<= 0.25) | PASS 0.141 | PASS 0.096 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | PASS 0.545 (73 trades) | **FAIL** 0.315 (84 trades) |
| Parameter sensitivity (relative_std <= 0.5, window in {3,5,8} sweep) | **FAIL** 0.760 | PASS 0.232 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **REJECTED**

Sharpe fails decisively on both QQQ (0.709) and SPY (0.560) over the full
unconditional sample -- well short of the 1.0 threshold, even though MDD is
comfortably fine for both. QQQ additionally fails parameter sensitivity
(relative_std=0.76, driven by the window=8 config collapsing to near-zero
Sharpe in the low-vol slice), and SPY fails transaction-cost survival. As
with the MESA Sine Wave test earlier this run (2026-09-05-069), the entire
grid edge is concentrated in the equity low-vol tercile and evaporates once
averaged across the full unconditional sample or tested on crypto. Not
revisited further this iteration; a future loop could try gating entries by
an explicit low-vol-regime filter if this indicator family is worth another
look.
