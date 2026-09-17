# MHL (Middle-High-Low) Moving Average Crossover (Apirine, TASC Aug 2016) — Accepted (QQQ only)

**Source:** https://traders.com/Documentation/FEEDbk_docs/2016/08/TradersTips.html
(Vitali Apirine, "The Middle-High-Low Moving Average", TASC Aug 2016;
TradeStation EasyLanguage code disclosed)

**Hypothesis:** MHL = midpoint of the mhl_length-day high/low range,
smoothed by a moving_avg_length-period moving average. Compared against a
parallel close-based moving average of the same length/type. Source's own
mechanical rule: go long when the price-average crosses over the MHL
average (translated to flat/exit on the reverse cross since this repo is
long-only per SAFETY.md).

## Grid summary (144 cells: 2 mhl_length x 3 moving_avg_length x 2 avg_type
x 4 symbols x 3 vol regimes)

- pass_fraction: 0.3333 (48/144) — strong overall result
- by_asset_class: equity 33/72, crypto 15/72
- by_vol_regime: low 30/48, mid 15/48, high 3/48
- best avg-Sharpe config passing ALL 3 regimes: QQQ, avg_type=ema,
  mhl_length=10, moving_avg_length=75, avg Sharpe 1.38 (3/3 regimes passed)

## Single-config validation (QQQ, avg_type=ema, mhl_length=10,
moving_avg_length=75)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.222 | >= 1.0 | PASS |
| Max drawdown | 12.9% | <= 25% | PASS |
| TC survival (net Sharpe, 13 trades) | 1.197 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 0.75 (3/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (relative std) | 0.329 | <= 0.5 | PASS |

SPY cross-check at the same config: Sharpe 0.432 (FAIL), MDD 28.9% (FAIL),
13 trades — does not generalize to SPY.

## Verdict: ACCEPTED (QQQ only)

All 5 validators pass for QQQ with a solid drawdown profile (12.9%) and
reasonable trade count (13 over 2019-2026). Does not generalize to SPY
(fails both Sharpe and MDD at the identical config) or to crypto (best
single-vol-regime cells look promising, e.g. BTC/USDT Sharpe 1.15, but no
crypto symbol/config passed all 3 vol regimes the way QQQ did). This is a
QQQ-specific edge from the MHL-vs-price EMA crossover mechanism.
