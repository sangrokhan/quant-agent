# RSI dip-buy + ATR hard stop + recent-high take-profit, trend-gated (REJECTED)

**Hypothesis:** per Arrow Algo's "Buy the Dip Strategy: Trade Pullbacks With
Rules" (https://arrowalgo.com/buy-the-dip-strategy), a systematic dip buy
combines (1) close > SMA(200) trend gate, (2) RSI(14) crossing below 30 as
the dip trigger, (3) a hard stop at 1.5x ATR below the dip-day low, and (4) a
take-profit at the rolling recent high (20-day lookback), falling back to a
15-day time-stop since this repo trades close-to-close (no true intrabar
stop fills).

Strategy file: `strategies/2026-09-23_rsi_dip_atr_stop_trend_gate.py`

## Step 6 grid summary (rsi_threshold in [25,30] x atr_mult in [1.5,2.5], equity QQQ/SPY + crypto BTC/USDT, vol_regime_splits=3)

- total_cells: 36, passed_cells: 9, **pass_fraction: 0.25**
- by_asset_class: equity 7/24 passed, crypto 2/12 passed
- by_vol_regime: low 0/12, mid 4/12, high 5/12 — edge (what little there is) concentrated in higher-vol terciles, essentially absent in low-vol regime
- best_cell: rsi_threshold=25, atr_mult=1.5, SPY, high-vol regime, Sharpe 1.765
- worst_cell: rsi_threshold=25, atr_mult=1.5, BTC/USDT, low-vol regime, Sharpe -0.656

## Step 7 single-config validation (best config: rsi_threshold=25, atr_mult=1.5, full sample 2019-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| SPY | 0.771 (FAIL, thr 1.0) | 0.072 (PASS, thr 0.25) | 0.732 (PASS, thr 0.5) | skipped (vectorbt API mismatch in this env: `vectorbt.utils.splitting` not found) | 0.210 (PASS, thr 0.5) |
| QQQ | 0.441 (FAIL, thr 1.0) | 0.113 (PASS, thr 0.25) | 0.417 (FAIL, thr 0.5) | skipped (same API mismatch) | 0.240 (PASS, thr 0.5) |

Only 9 trades over the full ~7.5yr sample on each symbol — a fixed
threshold-based dip entry is rare given the AND-gate of trend+RSI+ATR/TP
freeze logic.

## Decision: REJECTED

Full-sample Sharpe fails the 1.0 threshold on both SPY and QQQ (the two
symbols with the best grid pass-rate); QQQ additionally fails transaction
cost survival. Walk-forward validator hit an environment-level vectorbt API
issue (`vectorbt.utils.splitting.RangeSplitter` unavailable in this venv's
vectorbt version) and was skipped rather than blocking the whole iteration —
acceptable under `suggested_workload=light`, but noted here since it's an
existing gap, not evidence for/against the strategy. Grid `pass_fraction`
of 0.25 and the low-vol-regime 0/12 result corroborate the single-config
failure: the edge, where present at all, only shows up in high-vol
regimes/cells and is not broad enough to accept.
