# Backtest Report: Accumulation/Distribution Line Slope + SMA Trend Filter

**Strategy file:** `strategies/2026-09-04_ad_line_slope_trend.py`
**Knowledge base id:** 2026-09-04-047

## Hypothesis

Per TradingBrokers.com's Accumulation/Distribution guide (Marc Chaikin,
1980s): the A/D Line — a cumulative running total of intrabar
close-position-weighted volume — rising while price is above a moving
average confirms uptrend strength. Long entry: A/D's own smoothed slope
rising AND close > SMA(trend_window); exit when either condition breaks.
A hybrid of CMF's (accepted -043) intrabar-position weighting with OBV's
(accepted -027) cumulative-running-total structure.

Source: `https://tradingbrokers.com/accumulation-distribution-indicator-strategy/`
(fetched via `browser_exec` after `web_extract` failed with the recurring
DuckDuckGo/ddgs search-only-backend error).

## Grid test summary (Step 6)

Grid: `slope_window` in {5, 10, 20} x `trend_window` in {50, 200} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells.

- `pass_fraction`: 0.25 (18/72)
- `by_asset_class`: equity 18/36, crypto 0/36
- `by_vol_regime`: low 12/24, mid 6/24, high 0/24
- `best_cell` (low-vol-tercile artifact): QQQ, slope_window=10,
  trend_window=200, Sharpe 3.29

## Full-sample sweep (QQQ / SPY)

| slope_window | trend_window | QQQ Sharpe | SPY Sharpe |
|---|---|---|---|
| 5  | 50  | 0.766 | 0.643 |
| 5  | 200 | 0.661 | 0.826 |
| 10 | 50  | **1.212** | 0.848 |
| 10 | 200 | 1.167 | 0.906 |
| 20 | 50  | 0.863 | 0.476 |
| 20 | 200 | 1.040 | 0.425 |

Primary config: `slope_window=10, trend_window=50` — best full-sample
Sharpe on QQQ.

## Primary config validators (QQQ, slope_window=10, trend_window=50)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.212 | 1.0 |
| Max drawdown | ✅ | 0.195 | 0.25 |
| Transaction cost survival | ✅ | 1.136 (55 trades @ 10bps) | 0.5 |
| Walk-forward (4 splits, manual date-slice fallback) | ✅ | 1.0 (4/4 splits positive) | 0.75 |
| Parameter sensitivity (slope_window in {5,10,20}, trend_window=50 fixed) | ✅ | rel.std 0.202 | 0.5 |

**All 5 validators pass on QQQ.**

### SPY (same config)

Sharpe 0.848 (fails, 15% shortfall) — near-miss, MDD/TC/param-sens all
pass. Not accepted.

### Crypto

0/36 grid cells passed — decisively rejected.

## Outcome

**Accepted for QQQ only.** SPY near-miss (Sharpe 0.848). Crypto rejected
decisively.

## Notes

Walk-forward used the manual date-slice fallback per the documented
`vectorbt.utils.splitting` API bug. Novelty: first hybrid
cumulative-running-total + intrabar-position-weighted volume indicator
tested in this repo — distinct from both OBV (2026-09-04-027, uses only
the sign of daily close change, not intrabar position) and CMF
(2026-09-04-043, bounded rolling-window ratio, not a cumulative total).
