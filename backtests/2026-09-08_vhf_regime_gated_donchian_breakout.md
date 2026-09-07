# VHF Regime-Gated Donchian Breakout — Backtest Report

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_vhf_regime_gated_donchian_breakout.py`
**Source:** https://trendsandbreakouts.com/vertical-horizontal-filter (Adam White's
Vertical Horizontal Filter formula + the article's own stated "practical rule":
only take trend-following breakout trades when price is above a rising baseline
AND VHF is rising from a relatively low area, with a Donchian/Supertrend
supplying the actual breakout trigger).

## Hypothesis

VHF(28) trend-efficiency gate (>= threshold and rising) combined with a rising
SMA(50) baseline and a 20/10-day asymmetric Donchian breakout/exit, long-only,
on QQQ/SPY/BTC-USDT/ETH-USDT.

## Grid summary (Step 6)

`param_grid={vhf_threshold: [0.30, 0.35, 0.40], donchian_window: [20, 30]}`,
`symbols={equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`.

- total_cells=72, passed_cells=10, **pass_fraction=0.139**
- by_asset_class: equity 10/36, crypto 0/36 (decisive crypto rejection)
- by_vol_regime: low 6/24, mid 4/24, **high 0/24** (edge entirely concentrated
  in low/mid volatility regimes — high-vol tercile fails on every cell)
- by_symbol: QQQ 8/18, SPY 2/18, BTC/USDT 0/18, ETH/USDT 0/18
- best_cell: QQQ low-vol, vhf_threshold=0.30/donchian_window=20, Sharpe 1.36
- worst_cell: QQQ high-vol, vhf_threshold=0.40/donchian_window=20, Sharpe -1.40

## Single-config validation (Step 7): vhf_threshold=0.35, donchian_window=20

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.309 (FAIL) | -0.275 (FAIL) | >= 1.0 |
| Max drawdown | 0.139 (pass) | 0.138 (pass) | <= 0.25 |
| Net Sharpe after 10bps costs | 0.056 (FAIL) | -0.482 (FAIL) | >= 0.5 |
| Walk-forward (manual 4-split, vbt RangeSplitter broken) | 0.75, 3/4 (pass, borderline) | 0.25, 1/4 (FAIL) | >= 0.75 |
| Parameter sensitivity (6-cell relative std) | 1.014 (FAIL) | 0.322 (pass) | <= 0.5 |

Full-sample Sharpe collapses relative to the grid's isolated low/mid-vol
tercile Sharpes (1.28-1.36) because the strategy trades through the high-vol
tercile too whenever the VHF gate/SMA-rising condition happens to be
satisfied there, and those trades are decisively unprofitable (worst_cell
Sharpe -1.40). The gate as implemented doesn't fully exclude bad-regime
entries in practice, only partially.

## Decision: REJECTED (both QQQ and SPY)

Neither symbol clears the full-sample Sharpe/net-Sharpe bar despite grid
cells looking attractive when isolated to low/mid-vol slices. Crypto rejected
decisively (0/36). Not worth pursuing further without a stricter regime gate
(e.g. hard-excluding trades initiated during a live high-vol tercile
classification, rather than only gating on VHF/SMA slope) — flagged in
`notes` for a possible future follow-up.
