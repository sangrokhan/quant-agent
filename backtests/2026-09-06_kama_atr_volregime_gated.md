# Backtest Report: KAMA + ATR Volatility-Band, Explicit Vol-Regime Gate

**Strategy file:** `strategies/2026-09-06_kama_atr_volregime_gated.py`
**Date:** 2026-09-06
**Hypothesis id:** 2026-09-06-183

## Hypothesis

Direct follow-up to near-miss 2026-09-06-181 (plain KAMA/ATR-band crossover,
full-sample SPY Sharpe 0.894, near-miss vs 1.0 threshold; grid showed the
edge concentrated almost entirely in the low-vol tercile: 8/16 low-vol
cells passed vs only 1/16 high-vol cells). Tests whether adding an explicit
realized-vol-vs-trailing-median regime gate (identical construction to this
repo's accepted `2026-09-03_bb_meanrev_qqq_volregime.py`) restricts trading
to the regime where the edge concentrates and rescues the full-sample
Sharpe above 1.0.

## Step 6 grid summary

Param grid: `fast_sc_period in {2,3}` x `vol_regime_ratio in {0.9,1.0,1.2}`
(fixed `er_window=10, slow_sc_period=30, atr_window=14, atr_min_pct=0.005,
atr_max_pct=0.035, atr_exit_pct=0.06, vol_window=20, vol_lookback=252,
max_hold_days=40`), symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT,
ETH/USDT]}`, `vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **pass_fraction: 0.194** (14/72) -- *lower* than the ungated predecessor's
  0.271 (13/48)
- **by_asset_class:** equity 14/36; crypto 0/36 (still decisive fail)
- **by_vol_regime:** low 12/24, mid 2/24, high 0/24
- **best_cell:** `fast_sc_period=3, vol_regime_ratio=1.2`, SPY/low-vol,
  Sharpe 2.41 (essentially unchanged from predecessor's best cell of 2.40)

## Step 7 single-config validators (best config: SPY, `fast_sc_period=3,
vol_regime_ratio=1.2`, full sample 2018-2026-09)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ❌ | **0.747** (worse than predecessor's 0.894) | ≥ 1.0 |
| max_drawdown | ✅ | 0.176 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 91 trades) | ✅ | net Sharpe 0.563 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback) | ✅ | 4/4 splits positive | ≥ 0.75 |
| parameter_sensitivity (6-cell grid) | ✅ | relative std 0.296 | ≤ 0.5 |

## Decision: **REJECT (hypothesis falsified)**

The explicit vol-regime gate did NOT rescue the near-miss -- full-sample
Sharpe actually got *worse* (0.747 vs the ungated predecessor's 0.894). The
gate simply blocks additional trades (91 vs the predecessor's 109) that,
while individually somewhat weaker, weren't dragging the aggregate Sharpe
down enough to offset the opportunity cost of missing them; the low-vol
best-cell Sharpe (2.41) is essentially identical to the predecessor's best
cell (2.40), confirming the ATR-percent band in the original design was
*already* implicitly doing most of the regime-selection work the explicit
gate was meant to add. This falsifies the specific mechanism hypothesized
(that an explicit regime gate on top of the ATR band would help) --
contrast with the accepted `2026-09-03_bb_meanrev_qqq_volregime.py`, where
the vol-regime gate was the PRIMARY filter (no other volatility-aware
mechanism), not a redundant add-on to an already-volatility-sensitive entry
condition like KAMA/ATR-band. Not flagged for further revisiting along this
specific line; the underlying edge (KAMA/ATR-band, unconditional) remains a
recorded near-miss (2026-09-06-181) that could still be revisited via a
different rescue mechanism (e.g. tighter ATR band, different KAMA windows)
in a future iteration.
