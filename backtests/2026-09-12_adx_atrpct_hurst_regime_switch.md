# ADX / ATR-percentile / Hurst-exponent 3-filter regime-switch — REJECTED

**Strategy file:** `strategies/2026-09-12_adx_atrpct_hurst_regime_switch.py`
**Source:** https://fortraders.com/blog/momentum-vs-mean-reversion-strategies-for-challenges

## Hypothesis

Per the source article, three measurable filters jointly classify market
regime: ADX(14) > 25, ATR-percentile > 60th, Hurst > 0.55 → momentum mode
(EMA 12/26 crossover); ADX < 20, ATR-percentile < 40th, Hurst < 0.45 →
mean-reversion mode (20d z-score fade, entry_z=1.5-2.0); anything else →
flat ("no-regime zone"). This is the first strategy in this repo to combine
all three filters jointly into a single bimodal (switches strategy family)
system, distinct from prior single-filter Hurst gates (2026-09-04-155/156,
rejected) and various single ADX/ATR filters elsewhere in the repo.

## Grid test summary (Step 6)

- Grid: `adx_trend_th` in [20, 25], `hurst_mr_th` in [0.42, 0.45, 0.48],
  `entry_z` in [1.5, 2.0]; symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT
  (crypto); vol_regime_splits=3. 144 total cells.
- **pass_fraction: 0.125 (18/144)**
- by_asset_class: equity 18/72 passed; **crypto 0/72 (decisive fail)**
- by_vol_regime: low 12/48, mid **0/48 (decisive fail)**, high 6/48
- best_cell: adx_trend_th=25.0, hurst_mr_th=0.45, entry_z=1.5, SPY,
  high-vol regime, Sharpe 1.35 (single-tercile slice only, not full-sample)

## Single-config validation (Step 7) — best_cell params, full sample 2019-2026

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.482 ❌ | 0.561 ❌ | ≥ 1.0 |
| Max drawdown | 0.019 ✅ | 0.087 ✅ | ≤ 0.25 |
| TC survival (10bps/trade) | 0.301 ❌ | 0.444 ❌ | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-slice fallback, repo-known `vbt.utils.splitting` bug) | 0.75 ✅ (3/4) | 0.75 ✅ (3/4) | ≥ 0.75 |

## Decision: REJECTED

Full-sample Sharpe and transaction-cost survival both fail on both equity
symbols despite passing MDD and walk-forward. The grid's "best cell" Sharpe
of 1.35 was a single high-vol-tercile slice, not representative of the
full-sample performance — a case of overfitting to one regime slice. Crypto
rejected decisively (0/72), and mid-vol-regime equity rejected decisively
(0/48) — the strategy's "no-regime zone" flat-out logic combined with the
narrow trend/mean-reversion thresholds leaves it flat too often to generate
enough edge, and when it does trade, per-trade edge is too thin to survive
realistic transaction costs. Consistent with the repo's prior finding that
single-filter Hurst-exponent gates (2026-09-04-155/156) also failed —
adding two more joint filters (ADX, ATR-percentile) on top did not rescue
the underlying weak edge.
