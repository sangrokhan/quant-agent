# Backtest Report: DTI (Directional Trend Index) Zero-Line Crossover

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_dti_directional_trend_index.py`
**Source:** https://www.mql5.com/en/code/384, https://www.mql5.com/en/code/382,
https://www.mql5.com/en/articles/190 (William Blau's Composite High/Low
Momentum and Directional Trend Index, from "Momentum, Direction, and
Divergence")

## Hypothesis

DTI = 100 * triple-EMA-smoothed Composite High/Low Momentum (HLM) divided
by triple-EMA-smoothed |HLM|, where HLM(q) = HMU(q) - LMD(q) (up-trend
momentum minus down-trend momentum, built from High/Low rather than Close).
Signal: long when DTI crosses from <=0 to >0 (trend turning up); exit on
reverse cross or a max_hold_days time-stop. First DTI/Composite High-Low
Momentum strategy in this repo.

## Step 6 — Grid test summary

Grid: `r` (1st EMA smoothing period) in {10, 20, 30}, `max_hold_days` in
{20, 40, 60}, symbols {QQQ, SPY, BTC/USDT, ETH/USDT}, vol_regime_splits=3
(108 cells total). q=2, s=5, u=3 fixed at Blau's own defaults.

- **pass_fraction: 0.278** (30/108 cells)
- **by_asset_class:** equity 27/54 pass; crypto 3/54 (weak but non-zero)
- **by_vol_regime:** low-vol 21/36 pass; mid-vol 9/36 pass; high-vol 0/36 (decisive fail)
- **best_cell:** SPY, low-vol regime, `r=20, max_hold_days=20`, Sharpe 2.52
- **worst_cell:** QQQ, high-vol regime, `r=20, max_hold_days=60`, Sharpe -0.57

The strategy works as a trend-following, not mean-reversion, signal: it is
decisively disabled during high-vol regimes (whipsaw), consistent with
other trend-following strategies in this repo.

## Step 7 — Single-config validators (grid-best config: r=20, max_hold_days=20)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | near-miss FAIL 0.962 | **PASS** 1.117 |
| Max Drawdown (<=0.25) | **FAIL** 0.282 | PASS 0.146 |
| TC-survival (net Sharpe>=0.5, 10bps/trade) | PASS 0.847 | PASS 0.952 |
| Walk-forward | SKIPPED (pre-existing tooling bug: `vectorbt.utils` lacks `splitting` in the installed vectorbt version, not a strategy defect) |
| Parameter sensitivity (relative std <=0.5 across r={15,20,25}) | PASS 0.039 | PASS 0.075 |

## Step 8 — Decision

- **SPY: ACCEPT.** All runnable validators pass cleanly (Sharpe 1.117, MDD
  0.146, TC-survival 0.952, param-sensitivity relative std 0.075). Walk-forward
  skipped due to a pre-existing library incompatibility, noted per Step 7
  guidance for `suggested_workload=max` runs where this occurs.
- **QQQ: REJECT** (near-miss). Sharpe just short of the 1.0 threshold
  (0.962) and MDD exceeds the 0.25 cap (0.282) at this config -- a plausible
  future rescue is a tighter max_hold_days or an explicit high-vol-regime
  flatten gate, since the grid shows QQQ's high-vol cells are the main
  drag (worst_cell is QQQ high-vol).
- **Crypto (BTC/USDT, ETH/USDT): REJECT.** Only 3/54 grid cells pass;
  decisively unsuitable for this signal at any tested config.

Strategy file and this report are kept as a record (SPY-only live strategy).
