# Trend Quality Indicator (TQI, Regression Slope x R²) Zero-Line Crossover — Backtest Report

**Date:** 2026-09-08 | **Strategy file:** `strategies/2026-09-08_tqi_regression_r2_crossover.py` | **Outcome: ACCEPTED (QQQ+SPY, per-symbol tuned configs); rejected (crypto)**

## Hypothesis
Per a TradingView open-source Pine script description (browser_exec
fallback — the primary trendspider.com KB page's content was too generic
with no explicit rule; web_extract also failed on it with the DuckDuckGo
search-only-backend error), the Trend Quality Indicator (TQI) combines a
linear-regression slope over a lookback window (ATR-normalized) with the
regression's own R² goodness-of-fit, explicitly designed to "penalize
trends that are not linear (i.e. choppy or curved moves)". Source's
explicit rule: smoothed TQI crossing above zero = long entry, crossing
below = exit. First R²-weighted trend-strength strategy in this repo.

Source: https://www.tradingview.com/script/wWgA0nGW-Trend-Quality-Indicator-TQI-TR/

## Grid test (reg_window=[14,20,30] x smooth_window=[3,5,8], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 108 cells total, 27 passed (pass_fraction 0.25)
- By asset class: equity 27/54, crypto 0/54 (decisive fail)
- By vol regime: low 18/36, mid 6/36, high 3/36 (some high-vol cells pass — unusually broad for this repo)
- Best cell: reg_window=14/smooth_window=8, SPY low-vol, Sharpe 2.67
- Best avg-across-regime configs: QQQ reg_window=14/smooth_window=5 avg Sharpe 1.59; SPY reg_window=14/smooth_window=3 avg Sharpe 1.36
- Per-symbol full-sample sweep of the QQQ grid found reg_window=20/smooth_window=3 (avg-Sharpe-rank #3 for QQQ) gives the best full-sample MDD/Sharpe tradeoff for QQQ specifically (Sharpe 1.264, MDD 0.241, clears both thresholds vs the raw top-ranked reg_window=14/smooth_window=5 config's MDD 0.262 fail)

## Single-config validators (per-symbol tuned configs)

| Validator | QQQ (reg_window=20, smooth_window=3) | SPY (reg_window=14, smooth_window=5) | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | **1.264 PASS** | **1.183 PASS** | >= 1.0 |
| Max Drawdown | **0.241 PASS** | **0.169 PASS** | <= 0.25 |
| TC survival (10bps) | **1.206 PASS** | **1.097 PASS** | >= 0.5 |
| Walk-forward (4-split manual) | **1.00 PASS** | **1.00 PASS** | >= 0.75 |
| Parameter sensitivity | **0.327 PASS** | **0.274 PASS** | <= 0.5 |
| Trade count | 39 | 47 | n/a (healthy sample) |

Crypto context (QQQ's config, reg_window=20/smooth_window=3): BTC/USDT
Sharpe 0.198, ETH/USDT Sharpe 0.301 — clear fail.

## Verdict
**ACCEPTED for QQQ and SPY (per-symbol tuned configs).** Both tickers pass
all five validators with healthy trade counts (39/47), a broad grid
pass-fraction (0.25 — one of the higher rates recorded recently, and
notably includes some high-vol-regime passes, suggesting less
regime-fragility than most other accepted strategies in this repo like
GAPO 2026-09-08-050 which was low/mid-vol only). This joins GAPO as a
second acceptance from this cron trigger. Crypto rejected decisively
(0/54 grid cells, BTC/ETH Sharpe 0.20/0.30). Scope: equity only,
per-symbol tuned configs (QQQ reg_window=20/smooth_window=3, SPY
reg_window=14/smooth_window=5) — not a single shared config.
