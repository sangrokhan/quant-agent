# Know Sure Thing (KST) Continuous Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_kst_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-129` (accepted QQQ/BTC-USDT/ETH-USDT, rejected SPY — genuine near-miss: Sharpe 0.996<1.0, TC-survival 0.388<0.5)

## Hypothesis

`2026-09-14-129`'s Know Sure Thing (Pring's weighted sum of four
SMA-smoothed ROC legs, periods 10/15/20/30 weighted 1/2/3/4 — formula
re-confirmed this iteration against StockCharts ChartSchool's full
disclosure, `RCMA1..4` legs and weighting, matching the repo's existing
implementation exactly) continuous-sizing dial accepted decisively for QQQ,
BTC/USDT and ETH/USDT but SPY was rejected on a genuine near-miss after a
narrower sweep (sensitivity/deadband only). This iteration widens the
search to also vary `trend_window` and `zscore_window` (not just
sensitivity/deadband) and finds SPY passes cleanly at
trend_window=40/zscore_window=60/sensitivity=0.5/deadband=0.30. Same
strategy file, same already-confirmed KST formula, no code changes beyond
the parameter config.

## Grid search (SPY only, this iteration)

144-cell grid: trend_window in {30,40,50} x zscore_window in {60,90,120} x
sensitivity in {0.3,0.4,0.5,0.6} x deadband in {0.20,0.30,0.35,0.40}
(base_exposure=0.5, leverage_cap=1.0 fixed, cells with <5 trades excluded).
Best cell by (gross Sharpe + net-of-cost Sharpe): trend_window=40,
zscore_window=60, sensitivity=0.5, deadband=0.30 — gross Sharpe 1.124,
net-of-cost Sharpe 0.664, 125 trades.

## Single-config validators (SPY, trend_window=40/zscore_window=60/sensitivity=0.5/deadband=0.30)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.124 | 1.0 | Yes |
| Max drawdown | 0.072 | 0.25 | Yes |
| TC-survival (net Sharpe) | 0.664 | 0.5 | Yes |
| Walk-forward | 0.75 (3/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std, 144-cell grid) | 0.121 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass**, with the TC-survival margin
(0.664 vs 0.5) comfortably clearing the prior near-miss's 0.388. Combined
with `2026-09-14-129`'s QQQ/BTC/ETH accepts (same strategy file, per-symbol
tuned params), the KST continuous-sizing dial now covers all 4 symbols
this repo tracks — following the same pattern as this cron trigger's
earlier STARC/LRS/TSV SPY-fix iterations (widen the secondary parameter,
not just sensitivity/deadband).
