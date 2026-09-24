# Backtest report: 3DC (3-day trend compression), downtrend reversal long

**Strategy file:** `strategies/2026-09-24_3dc_downtrend_reversal.py`
**Hypothesis source:** https://thepatternsite.com/3DC.html (Thomas Bulkowski's write-up of Andrea Unger's "The Trend Compression Pattern," TASC Feb 2024; browser_exec fallback — web_search's DDGS backend cannot usefully extract thepatternsite.com)

## Hypothesis

3DC is a pure volatility-compression 3-bar pattern (3rd bar's range less
than 1/3 of the sum of the first two bars' ranges, no directional/overlap
requirement). Source's own disclosed testing shows it performs best in
stocks specifically as a DOWNTREND reversal ($104.70 avg profit/trade vs
$83.91 benchmark) and underperforms in cryptocurrency. This strategy
targets exactly that context: downtrend + compression, long entry on
close above pattern high, source's own disclosed 2x-height Measure Rule
target.

## Grid test summary (Step 6)

`param_grid`: trend_window ∈ {10,20,30}, compression_ratio ∈
{0.25,0.33,0.5}, target_mult ∈ {1.5,2.0}; symbols: equity {QQQ, SPY},
crypto {BTC/USDT, ETH/USDT}; vol_regime_splits=3; period 2019-01-01 to
2026-09-01.

- **total_cells:** 216
- **passed_cells:** 51
- **pass_fraction:** 0.236
- **by_asset_class:** equity 49/108, crypto 2/108 (confirms source's own disclosed crypto underperformance)
- **by_vol_regime:** low 31/72, mid 17/72, high 3/72
- **0/216 cells errored** (unlike this cron trigger's two prior grid-passing-but-full-sample-failing candidates, Shark-32/Horn Bottom, which had 42-186 empty/no-trade cells) — 3DC produces a healthy trade density across the whole grid, a positive sign against the regime-cherrypicking concern raised for those two.
- **best_cell:** trend_window=10, compression_ratio=0.33, target_mult=2.0, SPY low-vol, Sharpe=2.909
- Most robust config: trend_window∈{10,20}, compression_ratio=0.5, target_mult∈{1.5,2.0} (4/12 vol-regime x symbol cells each).

## Single-config validation (Step 7) — SPY & QQQ, trend_window=10, compression_ratio=0.5, target_mult=1.5, full sample 2019-2026

Unlike the prior two rejections this cron trigger, this config has a
healthy trade count (137 SPY / 159 QQQ trades over 8 years, ~1100+
nonzero-return days each) — no low-trade-count/regime-cherrypick concern
here.

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL 0.902 | **PASS** 1.012 | ≥ 1.0 |
| Max drawdown | **FAIL** 0.287 | **FAIL** 0.381 | ≤ 0.25 |
| Transaction cost survival | PASS 0.680 | PASS 0.792 | ≥ 0.5 |
| Walk-forward (4 splits) | PASS 0.75 | PASS 0.75 | ≥ 0.75 |
| Parameter sensitivity | **FAIL** relative std 1.023 | **FAIL** relative std 1.540 | ≤ 0.5 |

QQQ narrowly passes Sharpe (1.012 vs 1.0) but both symbols fail max
drawdown decisively (0.29/0.38 vs 0.25 threshold — this compression
pattern, while frequent and Sharpe-competitive, exposes the portfolio to
larger drawdowns than the risk budget allows) and both fail parameter
sensitivity (relative std >1.0, well above the 0.5 threshold — grid
Sharpe varies too much across nearby parameter choices to trust this
exact configuration).

## Decision (Step 8): REJECT

2 of 5 validators fail for QQQ (max drawdown, parameter sensitivity), 3
of 5 fail for SPY (Sharpe, max drawdown, parameter sensitivity) — reject
per Step 8's all-must-pass criterion on both symbols. Unlike Shark-32 and
Horn Bottom (this cron trigger's two prior rejections), this is NOT a
low-trade-count/regime-cherrypick artifact — the pattern has genuine,
frequent signal and a real (if imperfect) edge, but the realized max
drawdown and cross-parameter instability are too large to accept as-is.
A future iteration could revisit this with an added volatility-regime
gate or tighter stop-loss to control drawdown, noting this as a
"near-miss worth revisiting with a tweak" per RESEARCH_LOOP.md Step 1
guidance.

Strategy/report/grid files are kept in the repo as a record of a rejected
attempt (not a live strategy).
