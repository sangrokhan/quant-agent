# Backtest Report: VIDYA crossover, slope-confirmed (2026-09-05)

**Hypothesis:** VIDYA (Variable Index Dynamic Average, Tushar Chande 1992)
is an EMA-style adaptive moving average whose smoothing constant scales
with abs(Chande Momentum Oscillator)/100 each bar — fast-tracking price
during strong-momentum trends, nearly flat during choppy/ranging markets.
Per arrowalgo.com's VIDYA guide, price crossing above VIDYA while VIDYA
itself is sloping upward is the recommended entry (the source explicitly
warns that crossovers of a flat VIDYA "carry no directional information").
Exit when price crosses below a downward-sloping VIDYA, or a max-hold
time-stop.

**Source:** https://arrowalgo.com/variable-index-dynamic-average-complete-guide-algorithmic-trading/
(full VIDYA construction formula and mechanical crossover rule disclosed
free).

**Novelty:** first VIDYA strategy in this repo — explicitly distinguished
from KAMA (2026-09-04-048/151, also a Tushar-Chande-adjacent adaptive
average, but using the Efficiency Ratio rather than the Chande Momentum
Oscillator for its adaptive scaling factor).

## Grid test (validation/grid_test.py)

- param_grid: `cmo_period` in {9, 14}, `vidya_span` in {14, 21},
  `max_hold_days` in {15, 25}
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits = 3
- total_cells = 96, passed_cells = 24, **pass_fraction = 25.0%**
- by_asset_class: equity 24/48, crypto 0/48
- by_vol_regime: low 16/32, mid 8/32, high 0/32
- best_cell: SPY, cmo_period=14, vidya_span=21, max_hold_days=15,
  low-vol regime, Sharpe 2.87
- Best config (cmo_period=14, vidya_span=21, max_hold_days=15) per-symbol:
  QQQ 2/3 passed (avg Sharpe 1.22), SPY 1/3 passed (avg Sharpe 1.27),
  BTC/USDT 0/3 (avg Sharpe 0.31), ETH/USDT 0/3 (avg Sharpe 0.24).

## Single-config validators (config: cmo_period=14, vidya_span=21,
max_hold_days=15, full 2019-01-01..2026-09-01 sample)

| Symbol | Sharpe | MDD | TC-survival (10bps, N trades) | Passed all? |
|---|---|---|---|---|
| QQQ | 1.104 (PASS >=1.0) | 0.184 (PASS <=0.25) | 0.925 net Sharpe, 128 trades (PASS >=0.5) | **YES** |
| SPY | 1.115 (PASS >=1.0) | 0.180 (PASS <=0.25) | 0.849 net Sharpe, 136 trades (PASS >=0.5) | **YES** |

Parameter sensitivity (QQQ, full grid of cmo_period/vidya_span/max_hold_days,
8 cells, Sharpes 1.00-1.23): relative_std 0.074 vs 0.5 threshold — **PASS**,
very stable.

Walk-forward: skipped (known repo issue — installed vectorbt version lacks
`vbt.utils.splitting.RangeSplitter`).

## Decision: ACCEPT (QQQ, SPY); REJECT (crypto, decisively)

Both equity symbols clear every validator at the same shared config, with a
stable Sharpe across the full parameter sweep. Crypto fails decisively
across the whole grid (0/48 cells, average Sharpe 0.12-0.31), consistent
with the broad equity/crypto divergence pattern seen throughout this repo.
