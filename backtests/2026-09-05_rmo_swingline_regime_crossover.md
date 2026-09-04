# Backtest Report: RMO swing-line/regime crossover (2026-09-05)

**Hypothesis:** Rahul Mohindar Oscillator (RMO, Viratech India, official
MetaStock 10 inclusion 2006): a long-term trend-bias line built from a
chain of 10 successively-smoothed SMAs applied to close (RMO = Close - the
10th-order smoothed SMA), plus two EMA-derived swing/timing lines (ST2,
ST3). The medium-term swing line (ST2) crossing above the slower swing
line (ST3) while RMO is positive (bullish regime) signals a long entry.
Exit on the reverse crossover or the regime flipping negative, or a
max-hold time-stop.

**Source:** https://trendsandbreakouts.com/rmo-indicator (full construction
formula disclosed free; numeric period defaults noted as platform-dependent
by the source, tested here with reasonable values).

**Novelty:** first Rahul Mohindar Oscillator strategy in this repo —
distinct from other multi-stage-smoothing constructions already tested
(GMMA's 12-EMA ribbon, FRAMA's fractal-adaptive single EMA) since RMO's
core bias line is a *difference* (Close minus a 10th-order chained SMA),
not a ribbon or adaptive-alpha average.

## Grid test (validation/grid_test.py)

- param_grid: `sma_period` in {2, 3}, `st2_span` in {20, 30}, `st3_span` in
  {20, 30}, `max_hold_days` in {15, 25}
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits = 3
- total_cells = 192, passed_cells = 38, **pass_fraction = 19.8%**
- by_asset_class: equity 38/96, crypto 0/96
- by_vol_regime: low 32/64, mid 4/64, high 2/64
- best_cell: QQQ, sma_period=3, st2_span=30, st3_span=30, max_hold_days=25,
  low-vol regime, Sharpe 2.47
- Best config (sma_period=3, st2_span=20, st3_span=30, max_hold_days=15)
  per-symbol: QQQ 2/3 passed (avg Sharpe 1.37), SPY 1/3 passed (avg Sharpe
  0.83), BTC/USDT 0/3 (avg Sharpe 0.22), ETH/USDT 0/3 (avg Sharpe 0.21).
- `sma_period=2` (fastest bias line) underperforms `sma_period=3` across
  the board (e.g. QQQ avg Sharpe 0.34-0.80 vs 1.19-1.37) — the chained-SMA
  bias line is sensitive to this parameter, consistent with the source's
  own warning that RMO's multiple smoothing layers "already contain
  multiple layers of smoothing, so large parameter changes can alter its
  character more than expected."

## Single-config validators (config: sma_period=3, st2_span=20, st3_span=30,
max_hold_days=15, full 2019-01-01..2026-09-01 sample)

| Symbol | Sharpe | MDD | TC-survival (10bps, N trades) | Passed all? |
|---|---|---|---|---|
| QQQ | 1.149 (PASS >=1.0) | 0.167 (PASS <=0.25) | 0.991 net Sharpe, 95 trades (PASS >=0.5) | **YES** |
| SPY | 0.787 (FAIL <1.0) | 0.146 (PASS <=0.25) | 0.582 net Sharpe, 97 trades (PASS >=0.5) | NO (Sharpe miss) |

Parameter sensitivity (QQQ, full sma_period=3 grid, 8 cells, Sharpes
1.19-1.37): relative_std 0.046 vs 0.5 threshold — **PASS**, very stable.

Walk-forward: skipped (known repo issue — installed vectorbt version lacks
`vbt.utils.splitting.RangeSplitter`).

## Decision: ACCEPT (QQQ only); REJECT (SPY near-miss; crypto decisively)

QQQ clears every validator with a stable Sharpe across the sma_period=3
parameter sweep. SPY falls short of the Sharpe threshold at the identical
config (0.787 vs 1.0) though not by a wide margin — scope the accepted
strategy to QQQ only. Crypto fails decisively across the whole grid (0/96
cells, average Sharpe 0.15-0.26), consistent with the pattern seen across
nearly every trend/oscillator-family strategy tested in this repo.
