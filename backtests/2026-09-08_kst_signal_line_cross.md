# KST (Know Sure Thing) Signal-Line Crossover — Backtest Report

**Date:** 2026-09-08 | **Strategy file:** `strategies/2026-09-08_kst_signal_line_cross.py` | **Outcome: REJECTED**

## Hypothesis
Per gocharting.com's KST oscillator docs (browser_exec fallback — web_extract
failed, DuckDuckGo search-only backend), Pring's KST is a smoothed weighted
sum of 4 ROC readings for catching *major* trend changes. Source's explicit
rule: apply to weekly charts, long when KST crosses above its signal line
after having been negative, exit on the reverse cross. We approximate
"weekly" via a `scale` multiplier on the standard daily ROC/SMA periods.

Source: https://gocharting.com/docs/charting/technical-indicator/oscillators/know-sure-things

## Grid test (scale=[3,5,7] x signal_window=[6,9], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 72 cells total, 12 passed (pass_fraction 0.167)
- By asset class: equity 12/36 passed, crypto 0/36 (decisive fail)
- By vol regime: low 8/24, mid 4/24, high 0/24 — only works in calm markets
- Best cell: scale=3/signal_window=6, QQQ low-vol, Sharpe 2.07
- Worst cell: scale=5/signal_window=6, QQQ high-vol, Sharpe -0.70
- Best avg-across-vol-regime config: QQQ scale=3/sw=6 avg Sharpe 1.06, SPY same config avg Sharpe 0.77

## Single-config validators (scale=3, signal_window=6, lookback_neg=20, max_hold_days=40)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.382 **FAIL** | 0.357 **FAIL** | >= 1.0 |
| Max Drawdown | 0.207 PASS | 0.170 PASS | <= 0.25 |
| TC survival (10bps, num_trades=8/10) | 0.367 **FAIL** | 0.335 **FAIL** | >= 0.5 |
| Walk-forward (4-split, manual — vectorbt RangeSplitter still broken) | 0.75 PASS | 0.75 PASS | >= 0.75 |
| Parameter sensitivity (relative std, scale x signal_window grid) | 8.58 **FAIL** | 0.295 PASS | <= 0.5 |

## Verdict
**REJECTED.** Full-sample Sharpe on both QQQ and SPY (0.38, 0.36) falls well
short of the grid's cherry-picked low-vol-only best cells (Sharpe up to
2.07) — a classic regime-dependence signature the grid pass_fraction (only
0.167) already flagged. Crypto rejected decisively (0/36). QQQ additionally
fails parameter sensitivity badly (relative std 8.58 — a couple of
scale/signal_window combos flip to slightly negative Sharpe, blowing up the
ratio around a near-zero mean). Confirms the source's own explicit caution
that KST "should not be used for short-term trading" — our daily-bar
approximation of "weekly" via the `scale` multiplier does not adequately
substitute for genuine weekly-bar data, and the strategy only works in
narrow low-vol equity slices.
