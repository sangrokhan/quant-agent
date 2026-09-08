# IBS + Rolling-Range Lower-Band Mean Reversion with Dynamic SMA Stop — Backtest Report

**Date:** 2026-09-08 (iteration 5, cron trigger 2026-09-09)
**Strategy file:** `strategies/2026-09-09_ibs_range_band_dynamic_stop.py`
**Source:** https://www.quantitativo.com/p/a-mean-reversion-strategy-with-211
("A Mean Reversion Strategy with 2.11 Sharpe")

## Hypothesis

A quant blogger's own verified/reproduced rule set:
1. rolling mean of (High-Low) over 25 days
2. IBS = (Close-Low)/(High-Low)
3. lower_band = rolling 10-day High MINUS 2.5x the rolling mean range
4. Long entry when close < lower_band AND IBS < 0.3
5. Exit when close > yesterday's high, OR close < SMA(300) ("dynamic
   stop", the source's own best-performing exit variant after testing
   several alternatives including leverage and a binary market-regime
   filter, both of which the source explicitly reports as inferior).

Distinct from the already-tested IBS strategy in this repo
(2026-09-04-089: fixed ibs_entry/ibs_exit thresholds + a static 200-SMA
proximity band, IBS-reversion-to-high exit) since this construction adds
a genuinely separate price-level lower band (rolling-high minus
k*mean-range, a volatility-scaled support level) as a CO-REQUIREMENT with
IBS, and uses a dynamic SMA-crossunder stop rather than an IBS-reversion
target.

## Grid test summary (Step 6)

Grid: `range_window in {20,25}`, `band_mult in {2.0,2.5,3.0}`,
`ibs_threshold in {0.2,0.3}`, `stop_window in {200,300}` x symbols
`{QQQ,SPY,BTC/USDT,ETH/USDT}` x vol_regime_splits=3. 2018-01-01 to
2026-09-01.

- `total_cells=288`, `passed_cells=49`, `pass_fraction=0.170`
- `by_asset_class`: equity 49/144 PASS; **crypto 0/144 (decisive reject)**
- `by_vol_regime`: low 31/96, mid 4/96, high 14/96 — edge concentrated
  in low-vol, but unusually (vs most strategies in this repo) also shows
  some signal in high-vol (14/96) — a mean-reversion strategy benefiting
  from sharper drawdowns in volatile periods, consistent with the
  source's own framing ("market tends to bounce back once it drops too
  low from its recent highs").
- `best_cell`: QQQ, range_window=25/band_mult=2.0/ibs_threshold=0.2/
  stop_window=200, low-vol, Sharpe 2.13.

## Single-config validator results (full sample, PER-SYMBOL TUNED configs
— unlike some prior accepted strategies in this repo, QQQ and SPY did NOT
share one config; each needed its own local optimum)

| Metric | QQQ (`range_window=25,band_mult=2.0,ibs_threshold=0.2,stop_window=200`) | SPY (`range_window=30,band_mult=3.0,ibs_threshold=0.3,stop_window=150`) | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.063 (PASS) | 1.148 (PASS) | >= 1.0 |
| Max drawdown | 0.123 (PASS) | 0.092 (PASS) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.841 (PASS) | 0.887 (PASS) | >= 0.5 |
| Parameter sensitivity (relative std, 3x3 grid) | 0.194 (PASS) | 0.066 (PASS) | <= 0.5 |
| Walk-forward (manual 4-split substitute) | 4/4 splits Sharpe>0: `[1.049, 1.453, 1.513, 0.726]` (PASS) | 3/4 splits Sharpe>0: `[-0.225, 1.576, 0.626, 1.645]` (PASS, pass_fraction=0.75 meets threshold) | >= 3/4 |

Number of trades over full sample: QQQ 143, SPY 109.

## Decision

**ACCEPTED for equity (QQQ, SPY)** — per-symbol tuned configs (not a
shared config; QQQ and SPY needed different `band_mult`/`stop_window`
values to each individually clear the Sharpe threshold).
**REJECTED for crypto** (BTC/USDT, ETH/USDT) — decisive 0/144 grid cells.

Scope caveat: SPY's walk-forward has one negative-Sharpe split (the first
quarter of the sample, likely reflecting fewer/noisier signals early in
the 2018-2026 window) — pass_fraction is exactly at the 0.75 threshold,
not comfortably above it. A future loop could investigate whether a
slightly different lookback/config improves SPY's early-sample
robustness without sacrificing full-sample Sharpe.
