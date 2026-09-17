# Katsanos R-squared "Goldilocks zone" Trend System (TASC Oct 2016) — Rejected (near-miss)

**Source:** https://traders.com/Documentation/FEEDbk_docs/2016/10/TradersTips.html
(Markos Katsanos, "Which Trend Indicator Wins?", TASC Oct 2016; MetaStock
formula disclosed)

**Hypothesis:** Rolling R-squared (of a linear regression of close vs time)
must freshly cross above a lower threshold (0.42) while remaining below an
upper cap (0.85, avoiding overextended trends) and rising over a trailing
lookback, AND the regression slope must be positive, AND close above its
50-day SMA. Exit: close crosses back below the SMA.

## Grid summary (144 cells: 3 r2_period x 2 slope_min x 2 max_hold_days x
4 symbols x 3 vol regimes)

- pass_fraction: 0.25 (36/144)
- by_asset_class: equity 22/72, crypto 14/72
- by_vol_regime: low 30/48, mid 6/48, **high 0/48** (fails completely in
  high-vol regimes across every asset class)
- best config by avg-Sharpe: QQQ, r2_period=25, max_hold_days=40,
  slope_min=0.0 — passed 2/3 regimes, avg Sharpe 0.97

## Single-config validation (QQQ, r2_period=25, max_hold_days=40,
slope_min=0.0)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.960 | >= 1.0 | FAIL (near-miss) |
| Max drawdown | 14.8% | <= 25% | PASS |
| TC survival (net Sharpe, 19 trades) | 0.921 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 1.0 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (relative std) | 0.223 | <= 0.5 | PASS |

## Verdict: REJECTED (near-miss)

4 of 5 validators pass cleanly (MDD, TC-survival, walk-forward, parameter
sensitivity all comfortably clear their thresholds), but full-sample Sharpe
0.960 falls just short of the 1.0 bar. High-vol regime performance was
uniformly negative across all symbols/configs (0/48), consistent with a
trend-quality gate that works well in calm/trending conditions but
whipsaws when volatility spikes. A future iteration could revisit this with
a slightly higher r2_enter threshold or a volatility-regime exit overlay to
push the near-miss Sharpe over 1.0.
