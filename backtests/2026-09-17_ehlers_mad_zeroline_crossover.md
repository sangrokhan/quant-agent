# 2026-09-17 — Ehlers MAD (Moving Average Difference) zero-line crossover

**Hypothesis:** John F. Ehlers' MAD indicator (TASC October 2021, "Cycle/Trend
Analytics And The MAD Indicator"), disclosed formula (TradingView Pine, via
https://traders.com/documentation/feedbk_docs/2021/10/traderstips.html):

    MAD = 100 * (SMA(close, shortLength) - SMA(close, longLength)) / SMA(close, longLength)

Default shortLength=8, longLength=23. Source plots green when MAD>0, red when
<0 (a percent-normalized dual-SMA-difference trend indicator). Long entry
when MAD crosses above zero AND close is above its own `trend_window`-day
SMA regime filter; exit on MAD crossing back below zero (with
`min_hold_days` hysteresis) or a `max_hold_days` time-stop.

## Grid summary (short_length={8,12} x long_length={23,30} x trend_window={100,150} x min_hold_days={5,10}, symbols equity={QQQ,SPY} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3, 2019-01-01 to 2026-09-01, 192 cells)

- Overall pass_fraction: 0.318 (61/192)
- By asset class: equity 48/96 passed, crypto 13/96 passed
- By vol regime: low 45/64, mid 16/64, high 0/64 (degrades in high-vol, expected for a pure trend-following construction)
- Best cell: SPY low-vol Sharpe 3.11 (short_length=8, long_length=23, trend_window=150, min_hold_days=10)
- Worst cell: QQQ high-vol Sharpe -1.12

## Single-best-config validators (short_length=8, long_length=23, trend_window=150, min_hold_days=5, max_hold_days=40, 2018-01-01 to 2026-09-01)

| Metric | QQQ | SPY | BTC/USDT | ETH/USDT | Threshold |
|---|---|---|---|---|---|
| Sharpe | 1.198 | 0.829 | 0.851 | 0.904 | >=1.0 |
| Max Drawdown | 0.161 | 0.136 | 0.587 | 0.435 | <=0.25 |
| TC-adjusted Sharpe | 1.050 | 0.630 | 0.809 | 0.874 | >=0.5 |
| Walk-forward (manual 4-slice) | 1.0 | 1.0 | 0.75 | 0.75 | >=0.75 |
| Parameter sensitivity (rel std) | 0.013 | 0.061 | 0.287 | 0.111 | <=0.5 |
| **Verdict** | **PASS all 5** | FAIL Sharpe (near-miss) | FAIL Sharpe+MDD | FAIL Sharpe+MDD |

## Verdict: ACCEPTED for QQQ only. REJECTED for SPY (Sharpe near-miss, otherwise clean), REJECTED for crypto (decisive MDD failure ~2x threshold on both BTC/USDT and ETH/USDT).

Kept as a QQQ-scoped strategy. SPY's near-miss (0.829 vs 1.0, all other 4
validators pass cleanly) is a natural candidate for a future fine-tune
sub-iteration (SPY-specific parameter search, same pattern used successfully
for the Vortex/Parabolic SAR SPY near-miss rescues in this repo). Crypto's
failure is a large MDD gap (0.587/0.435 vs 0.25 threshold, ~2x over) typical
of unscaled binary-exposure trend-following on crypto in this repo -- would
need a leverage-cap-aware inverse-vol sizing overlay (this repo's standard
fix pattern) to be worth revisiting.
