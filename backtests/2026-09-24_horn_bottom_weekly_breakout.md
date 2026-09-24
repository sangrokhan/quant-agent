# Backtest report: Bulkowski Horn Bottom (weekly-scale breakout)

**Strategy file:** `strategies/2026-09-24_horn_bottom_weekly_breakout.py`
**Hypothesis source:** https://thepatternsite.com/hornb.html (Thomas Bulkowski, browser_exec fallback — web_search's DDGS backend cannot usefully extract this domain)

## Hypothesis

Horn Bottom is a WEEKLY-scale H-shaped pattern (two low spikes separated
by a middle week, in a downtrend) that is one of the best-performing
patterns disclosed on thepatternsite.com: overall rank 2/3 at the weekly
scale, break-even failure only 6%, average rise 59%, 74% hit the disclosed
Measure Rule target. Daily OHLCV from `data/loaders.py` was resampled to
weekly bars (W-FRI) to identify the pattern per the source's explicit
weekly-scale requirement, with entry on weekly close above the 3-week
pattern high and the source's own disclosed Measure Rule exit.

## Grid test summary (Step 6)

`param_grid`: spike_min_pct ∈ {0.0,0.005,0.01}, target_pct ∈
{0.5,0.74,1.0}, max_hold_weeks ∈ {8,12}; symbols: equity {QQQ, SPY},
crypto {BTC/USDT, ETH/USDT}; vol_regime_splits=3; period 2019-01-01 to
2026-09-01.

- **total_cells:** 216
- **passed_cells:** 49
- **pass_fraction:** 0.227 (highest of this cron trigger's 5 iterations so far)
- **by_asset_class:** equity 45/108, crypto 4/108
- **by_vol_regime:** low 28/72, mid 20/72, high 1/72
- **best_cell:** spike_min_pct=0.0, target_pct=0.5, max_hold_weeks=8, SPY low-vol, Sharpe=2.197
- Most robust config across param sweep: spike_min_pct=0.01, target_pct=1.0, max_hold_weeks=12 (5/12 vol-regime x symbol cells passed).

## Single-config validation (Step 7) — SPY & QQQ, spike_min_pct=0.01, target_pct=1.0, max_hold_weeks=12, full sample 2019-2026

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** 0.393 | **FAIL** 0.382 | ≥ 1.0 |
| Max drawdown | PASS 0.098 | PASS 0.169 | ≤ 0.25 |
| Transaction cost survival | **FAIL** 0.376 (4 trades) | **FAIL** 0.366 (6 trades) | ≥ 0.5 |
| Walk-forward (4 splits) | PASS 1.0 | PASS 0.75 | ≥ 0.75 |
| Parameter sensitivity | **FAIL** relative std 2.774 | **FAIL** relative std 0.633 | ≤ 0.5 |

Extremely low trade counts (SPY: 4 trades over 8 years; QQQ: 6 trades) —
the weekly-scale pattern is genuinely rare on a single symbol's history,
consistent with the source's own disclosure that this pattern was
"discovered" specifically and studied on a large cross-sectional sample
(1,000+ perfect trades across many stocks), not a single-symbol
daily/weekly series.

## Decision (Step 8): REJECT

Same pattern as this cron trigger's Shark-32 rejection (2026-09-24-123):
the grid's headline pass_fraction (0.227, the highest yet this run) was
driven by favorable vol-regime slice cherry-picking rather than a genuine
full-sample edge. Full-sample single-config validation on both SPY and
QQQ fails Sharpe (0.39/0.38 vs 1.0 threshold), transaction-cost survival
(too few trades to amortize costs, though the drag itself is small), and
parameter sensitivity (relative std 2.77/0.63, both well above the 0.5
threshold) decisively. **3 of 5 validators failed on both symbols** —
reject per Step 8's all-must-pass criterion.

This strengthens a cross-iteration observation worth flagging for future
loops: this cron trigger's grid_test.py vol-regime-tercile slicing can
surface a much higher apparent pass_fraction than the pattern's true
full-sample behavior supports when trade counts are very low (single
digits) per slice — Step 7's full-sample validation remains essential
even when Step 6's grid summary looks promising.

Strategy/report/grid files are kept in the repo as a record of a rejected
attempt (not a live strategy).
