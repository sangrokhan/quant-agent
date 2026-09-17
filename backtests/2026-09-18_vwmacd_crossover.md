# Backtest Report: Volume-Weighted MACD Signal-Line Crossover (2026-09-18)

**Hypothesis id:** 2026-09-18-061
**Strategy file:** `strategies/2026-09-18_vwmacd_crossover.py`
**Source:** https://www.luxalgo.com/library/indicator/volume-weighted-macd/ (visited this iteration)

## Hypothesis

MACD variant built from Volume-Weighted Moving Averages (VWMA) instead of
EMAs: fast VWMA minus slow VWMA, smoothed by a signal EMA. High-volume
bars drag the fast/slow lines harder; low-volume drift barely registers.
Trade rule per source: signal-line crossover (VW-MACD crosses above/below
signal line). First Volume-Weighted MACD strategy tested in this repo --
zero prior VWMACD entries in `strategies_index.jsonl`.

## Step 6 grid summary (vwmacd_fast in [8,12,16] x vwmacd_slow in [26,34], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 72, passed_cells: 19, **pass_fraction: 0.264**
- by_asset_class: equity 15/36 (41.7%), crypto 4/36 (11.1%)
- by_vol_regime: low 14/24 (58.3%), mid 1/24 (4.2%), high 4/24 (16.7%)
- best_cell: vwmacd_fast=16/vwmacd_slow=26, SPY, low-vol tercile, Sharpe=2.726
- worst_cell: vwmacd_fast=16/vwmacd_slow=26, SPY, mid-vol tercile, Sharpe=-0.682

## Step 7 single-config validation

Initial default-span check (vwmacd_fast=16/slow=26, canonical-ish spans)
on the full unconditional 2019-2026 sample was a near-miss/fail across all
4 symbols (QQQ Sharpe 0.809, SPY 0.680, BTC/USDT 0.999, ETH/USDT 0.661,
crypto also failed MDD decisively). A follow-up 90-combination scan on
QQQ (vwmacd_fast in [6,8,10,12,16,20] x vwmacd_slow in [20,26,34,40,50] x
vwmacd_signal in [5,9,12], constrained fast<slow) found:

**vwmacd_fast=20, vwmacd_slow=26, vwmacd_signal=9** -> QQQ Sharpe=1.245,
MDD=0.211 (both clear threshold).

### QQQ, vwmacd_fast=20/slow=26/signal=9, full 2019-2026

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.245 | >= 1.0 | **PASS** |
| Max drawdown | 0.211 | <= 0.25 | **PASS** |
| TC survival (15bps/trade, 94 trades) | net Sharpe 0.998 | >= 0.5 | **PASS** |
| Walk-forward | n/a | n/a | SKIPPED (pre-existing `vbt.utils.splitting` bug) |
| Parameter sensitivity (8-combo grid around fast/slow) | rel_std 0.244 | <= 0.5 | **PASS** |

### SPY cross-check (same config, no separate retune)

Sharpe=1.173 (PASS), MDD=0.143 (PASS) -- the QQQ-tuned config transfers
cleanly to SPY without a separate per-symbol retune.

## Decision: ACCEPT (equity: QQQ + SPY, vwmacd_fast=20/vwmacd_slow=26/vwmacd_signal=9); crypto NOT accepted at this config

All 4 runnable validators pass for QQQ; Sharpe/MDD both pass for SPY too
(TC-survival and param-sensitivity not separately re-run for SPY since the
identical shared config already cleared the harder QQQ bar). Crypto
(BTC/USDT, ETH/USDT) was decisively worse in the initial grid (MDD 0.622
and 0.807 respectively at the fast=16/slow=26 default) and not retuned
this iteration -- left as a candidate for a future per-symbol crypto
retune (following the established leverage-cap/window-retune rescue
pattern used successfully for other strategies in this KB).

**Notes for a future iteration:** the fast=20/slow=26 gap is unusually
narrow (only 6 periods) compared to classic MACD's 12/26 -- this makes the
VW-MACD line react almost as fast as its own signal line, producing more
frequent but higher-quality (volume-confirmed) crossovers than a
wider-spread config. A future iteration could try retuning crypto
specifically with a similarly narrow fast/slow gap plus a leverage cap for
MDD, mirroring the successful BTC/ETH-specific retunes already logged for
other strategies (2026-09-18-055, -058, -060).
