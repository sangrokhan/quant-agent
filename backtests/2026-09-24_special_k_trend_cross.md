# Backtest Report: Pring's Special K, Trend-Confirmed 10-day-MA Crossover (QQQ, SPY)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_special_k_trend_cross.py`
**Sources:** https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/prings-special-k (exact 12-term weighted ROC-SMA formula, signal-line rule) and https://iqoptionwiki.com/martin-prings-special-k-indicator/ (EMA100 price-trend confirmation rule) — both read via browser_exec; web_extract failed (ddgs backend search-only).

## Hypothesis
Special K = 12-term weighted sum of SMA-smoothed ROC values (formula in
strategy docstring). Long when Special K crosses above its 10-day SMA
signal line AND price is above its 100-day EMA (primary-trend filter,
combining StockCharts' short-term signal-line-cross rule with
IQOptionWiki's price/EMA100 trend confirmation). First Special K strategy
in this repo (0 prior hits) — distinct from 11 prior Know Sure Thing (KST)
entries, Pring's other differently-weighted ROC indicator.

## Single-config validators (grid's best cell: max_hold_days=40, trend_ema=100)

### QQQ
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | **FAIL** | 0.395 | >= 1.0 |
| Max drawdown | PASS | 0.132 | <= 0.25 |
| Transaction cost survival (10bps, 23 trades) | **FAIL** | net Sharpe 0.348 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | known repo `vectorbt.utils.splitting` bug, light workload |
| Parameter sensitivity | PASS | rel_std 0.099 | <= 0.5 |

### SPY (near-miss)
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | **FAIL (near-miss)** | 0.737 | >= 1.0 |
| Max drawdown | PASS | 0.064 | <= 0.25 |
| Transaction cost survival (10bps, 21 trades) | PASS | net Sharpe 0.663 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | known repo bug |
| Parameter sensitivity | PASS | rel_std 0.207 | <= 0.5 |

## Grid summary (Step 6)
`param_grid={"max_hold_days": [20, 40], "trend_ema": [50, 100]}`,
`symbols={"equity": ["QQQ", "SPY"]}`, `vol_regime_splits=3` (light workload).

- total_cells: 24, passed_cells: 10, **pass_fraction: 0.417**
- by_vol_regime: low 8/8 PASS, mid 0/8 FAIL, high 2/8 PASS
- best_cell: max_hold_days=40, trend_ema=100, SPY, low-vol, Sharpe 2.057
- worst_cell: same params, QQQ, high-vol, Sharpe -0.597

## Decision: REJECT (both QQQ and SPY, full sample)
SPY is a genuine near-miss (only Sharpe fails, at 0.737 vs 1.0 threshold;
every other validator passes cleanly) — flagged as a rescue candidate for
a future iteration (e.g. tighter trend_ema or an added volatility-regime
gate, following this repo's established min-hold/regime-gate rescue
pattern). QQQ fails more decisively (Sharpe 0.395, TC-survival fails too).
