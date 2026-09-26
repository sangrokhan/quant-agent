# Backtest Report: True Strength Index (TSI) Bullish Divergence

**Strategy file:** `strategies/2026-09-26_tsi_bullish_divergence.py`
**KB id:** 2026-09-26-066
**Outcome:** REJECTED

## Hypothesis

Source: Google AI-overview + Quantified Strategies Substack summary
(browser_exec Google SERP fallback; web_search DDGS backend returning
"No results found" for this query). Bullish TSI divergence: price makes a
lower low while TSI (William Blau's double-smoothed momentum ratio,
long=25/short=13 standard) makes a higher low over the same swing —
downside momentum weakening. Entry armed by that divergence, fires on the
next TSI-crosses-above-signal event; exit on the bearish crossover or a
time-stop.

This repo has 7 prior TSI entries but all are crossover/threshold/
continuous-sizing constructions on the TSI **level** — none use a
price-vs-indicator divergence pattern (already applied elsewhere in this
KB to MFI/%B/EMV/OBV/CMF/Elder-Bull-Power/Force-Index/MACD-histogram/RVI,
but never yet to TSI). First TSI-divergence strategy in this repo.

## Grid summary (Step 6)

`param_grid={swing_window:[15,20], max_hold_days:[15,20,30]}`, symbols
equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), `vol_regime_splits=3`,
72 total cells.

| Metric | Value |
|---|---|
| pass_fraction | 0.139 (10/72) |
| by_asset_class | equity 6/36, crypto 4/36 |
| by_vol_regime | low 5/24, mid 2/24, high 3/24 |
| best_cell | ETH/USDT, swing_window=15, max_hold_days=20, low-vol tercile, Sharpe 1.31 |

Best pass_fraction of any divergence-construction tested this cron trigger,
but still concentrated in the low-vol tercile.

## Single-config validation (Step 7) — QQQ (best-represented asset class), full sample

| Config | Sharpe | Max Drawdown | Net Sharpe after costs |
|---|---|---|---|
| swing_window=15, max_hold_days=20 | **FAIL** 0.470 | PASS 0.184 | **FAIL** 0.341 |
| swing_window=15, max_hold_days=15 | **FAIL** 0.254 | PASS 0.186 | **FAIL** 0.112 |

Both configs fail the headline Sharpe (≥1.0) and cost-survival (≥0.5)
thresholds on the full sample despite passing MDD.

## Decision

**Reject.** Strategy file retained in `strategies/` as a rejected-attempt
record (not live).
