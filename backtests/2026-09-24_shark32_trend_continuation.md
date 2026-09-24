# Backtest report: Bulkowski Shark-32 (trend-continuation, long+short)

**Strategy file:** `strategies/2026-09-24_shark32_trend_continuation.py`
**Hypothesis source:** https://thepatternsite.com/Shark32.html (Thomas Bulkowski, browser_exec fallback — web_search's DDGS backend cannot usefully extract this domain)

## Hypothesis

Shark-32 (two consecutive inside days, a 3-bar pattern) acts as a
continuation pattern 60% of the time per the source's own testing (overall
rank 18/23 among small patterns, break-even failure 32%, average rise
11%, 72% hit the 2x-height Measure Rule target). The source's own explicit
trading tactic is "trade with the trend" — breakout direction should match
the inbound trend. This strategy trades only continuation-direction
breakouts (long in uptrends, short in downtrends) with the source's own
disclosed Measure Rule exit.

## Grid test summary (Step 6)

`param_grid`: trend_window ∈ {10,20,40}, target_mult ∈ {1.5,2.0,3.0},
max_hold_days ∈ {10,20}; symbols: equity {QQQ, SPY}, crypto {BTC/USDT,
ETH/USDT}; vol_regime_splits=3; period 2019-01-01 to 2026-09-01.

- **total_cells:** 216
- **passed_cells:** 22
- **pass_fraction:** 0.102
- **by_asset_class:** equity 16/108, crypto 6/108
- **by_vol_regime:** low 14/72, mid 8/72, **high 0/72**
- **best_cell:** trend_window=40, target_mult=3.0, max_hold_days=10, ETH/USDT mid-vol, Sharpe=1.660
- Most equity passes clustered on SPY low-vol tercile (e.g. Sharpe up to 1.554 at trend_window=10, target_mult=3.0); QQQ barely passed at only 2/108 cells.

## Single-config validation (Step 7) — SPY, trend_window=10, target_mult=3.0, max_hold_days=10, full sample 2019-2026

This config was selected as the grid's strongest, most-consistent SPY
setting. Full-sample (not just the low-vol tercile slice) validator
results:

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.129 | ≥ 1.0 |
| Max drawdown | PASS | 0.076 | ≤ 0.25 |
| Transaction cost survival | **FAIL** | net Sharpe 0.053 (14 trades, 10bps/trade) | ≥ 0.5 |
| Walk-forward (4 splits) | PASS | 0.75 pass fraction (3/4 splits Sharpe>0) | ≥ 0.75 |
| Parameter sensitivity | **FAIL** | relative std 3.338 across 18-cell SPY grid | ≤ 0.5 |

n position changes: 14 (very low trade count — only 72/1927 days have
nonzero position).

## Decision (Step 8): REJECT

The grid's headline pass_fraction (0.102, concentrated in the low-vol
tercile) was misleading: full-sample single-config validation on SPY
shows the pattern's real edge (Sharpe 0.129) collapses once evaluated
across the whole period rather than a favorable vol-regime slice alone —
consistent with a small-sample/regime-cherrypicking artifact rather than a
genuine edge. Transaction costs (only 14 trades over 8 years, but each one
material given the drag) and parameter sensitivity (relative std 3.34,
far above the 0.5 threshold) both fail decisively. **3 of 5 validators
failed** (Sharpe, transaction costs, parameter sensitivity) — reject per
Step 8 criteria (all validators must pass to accept).

Grid summary confirms this is not robust across vol regimes either: **0/72
high-vol cells passed** in any asset class, and equity performance was
essentially SPY-only (QQQ 2/108) even within the low-vol slice.

Strategy/report/grid files are kept in the repo as a record of a rejected
attempt (not a live strategy).
