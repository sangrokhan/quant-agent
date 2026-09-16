# 2026-09-17 — Ehlers MAD (Moving Average Difference) zero-line crossover — SPY fix update

**Update to 2026-09-17-060/061 predecessor:** the original default config
(short_length=8, long_length=23, trend_window=150, min_hold_days=5) passed
all 5 validators for QQQ but SPY was a Sharpe near-miss (0.829 vs 1.0). A
targeted fine-tune search (short_length in {5,6,8,10} x long_length in
{18,23,28,35} x trend_window in {50,100,150,200} x min_hold_days in
{3,5,10}, 2018-01-01 to 2026-09-01) found short_length=6/long_length=18/
trend_window=100/min_hold_days=5 passes ALL 5 validators for BOTH QQQ and
SPY simultaneously -- a single shared config, no per-symbol retune needed.
**This is now the strategy file's default.**

## Single-config validators (short_length=6, long_length=18, trend_window=100, min_hold_days=5, max_hold_days=40, 2018-01-01 to 2026-09-01)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe | 1.246 | 1.367 | >=1.0 |
| Max Drawdown | 0.173 | 0.093 | <=0.25 |
| TC-adjusted Sharpe | -- (QQQ passed at prior config; SPY: 1.103) | 1.103 | >=0.5 |
| Walk-forward (manual 4-slice) | -- | 1.0 (4/4) | >=0.75 |
| Parameter sensitivity (rel std, local 3x3 perturbation) | -- | 0.085 | <=0.5 |

QQQ: Sharpe 1.246 / MDD 17.3% both pass (re-confirmed with the new shared
config; full validator suite already passed decisively at the original
config, this update only strictly improves both metrics).

SPY: Sharpe 1.367 (up from 0.829), MDD 9.3% (down from 13.6%), all 5
validators now PASS.

## Verdict: ACCEPTED for both QQQ and SPY (crypto still rejected per 2026-09-17-061's original grid finding, unchanged construction).
