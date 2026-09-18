# CCI Correction (Weekly Bias, Daily Reversal) — Backtest Report

**Hypothesis:** Per StockCharts.com ChartSchool's "CCI Correction"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/cci-correction,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content; strategy attributed to Donald Lambert's CCI
guidelines): a dual-timeframe system -- (1) weekly 26-period CCI surge above
+100/below -100 sets a persistent bullish/bearish bias; (2) while bullish,
a daily CCI plunge below -100 marks a pullback within the bigger uptrend;
(3) the daily CCI's subsequent recovery back above the ZERO line (not the
full +100) confirms the pullback has reversed and the bigger trend is
resuming -- the actual entry trigger. This repo's daily-only data is
resampled internally to weekly bars (no look-ahead: the weekly bias is
shifted by 1 week before being forward-filled onto the daily index) to
faithfully reproduce the source's genuine dual-timeframe design.

**Source:** https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/cci-correction

## Grid summary (Step 6)

- Grid: weekly_window∈{26,52} × max_hold_days∈{40,60}, symbols={QQQ,SPY}×
  {BTC/USDT,ETH/USDT}, vol_regime_splits=3 (2015-01-01 to 2026-09-01).
- 48 total cells, 7 passed (pass_fraction=0.15) — low overall pass fraction,
  but concentrated entirely in equity.
- by_asset_class: equity 7/24; crypto 0/24 (decisive crypto failure).
- by_vol_regime: low 5/16, mid 1/16, high 1/16.
- Best cell: SPY weekly_window=52/max_hold_days=60, low-vol Sharpe=1.99.

## Full-sample parameter search + single-config validation (Step 7)

| Symbol | Best config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity (rel.std) |
|---|---|---|---|---|---|---|
| QQQ | weekly_window=52, daily_window=14, max_hold_days=60 | 1.031 (PASS) | 0.206 (PASS) | 1.006 (PASS) | 4/4=1.00 (PASS) | 0.285 (PASS) |
| SPY | weekly_window=26, daily_window=20, max_hold_days=60 | 1.176 (PASS) | 0.100 (PASS) | 1.144 (PASS) | 4/4=1.00 (PASS) | 0.339 (PASS) |
| BTC/USDT | weekly_window=52, daily_window=14, max_hold_days=60 | 0.550 (fail) | -- | -- | -- | -- |
| ETH/USDT | weekly_window=13, daily_window=14, max_hold_days=60 | 0.680 (fail) | -- | -- | -- | -- |

## Decision: ACCEPT (QQQ and SPY)

Both equity symbols clear all 5 validators, though parameter sensitivity is
higher than most other accepted strategies this trigger (rel.std 0.29-0.34,
still well under the 0.5 threshold but a wider dispersion than most) —
consistent with this being a low-frequency signal (39-53 trades over
11.5 years) where individual trade timing matters more. Crypto decisively
fails on both symbols at the full-sample level (Sharpe 0.55/0.68, well
below 1.0) despite some isolated grid-cell passes in extreme vol-regime
slices — the weekly-bias-plus-daily-zero-line-recovery mechanism does not
translate to crypto's faster/choppier regime structure. This strategy is
added to `strategies/` as a live QQQ+SPY strategy; crypto configs are
recorded here as rejected.
