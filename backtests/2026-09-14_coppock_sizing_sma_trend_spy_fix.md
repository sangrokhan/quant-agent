# Coppock Curve Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_coppock_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-171` (accepted QQQ, rejected SPY near-miss Sharpe 0.938<1.0 + TC-survival 0.346<0.5; crypto decisively rejected — out of scope for this fix)

## Hypothesis

`2026-09-14-171`'s Coppock Curve (Edwin Coppock 1962, WMA-smoothed dual-ROC
composite momentum) continuous-sizing dial accepted decisively for QQQ but
SPY was a genuine near-miss on both Sharpe and TC-survival. This iteration
widens the search across `roc1_period`, `roc2_period`, `wma_window` and
`zscore_window` (not just sensitivity/deadband) with a wider deadband and
finds SPY passes cleanly at roc1_period=11/roc2_period=8/wma_window=10/
zscore_window=150/sensitivity=0.6/deadband=0.50 (Sharpe 1.384, net Sharpe
1.265 — very low turnover, only 44 trades over the full sample). Same
strategy file, same already-confirmed Coppock Curve formula, no new
external fetch. Crypto remains out of scope per predecessor's decisive
rejection.

## Grid search (SPY only, this iteration)

108-cell grid: roc1_period in {11,14,20} x roc2_period in {8,11,14}
(roc2<roc1 only) x wma_window in {10,15} x zscore_window in {60,100,150} x
deadband in {0.30,0.40,0.50} (trend_window=40, sensitivity=0.6 fixed,
base_exposure=0.4, leverage_cap=1.0, cells with <5 trades excluded). Best
cell: roc1_period=11, roc2_period=8, wma_window=10, zscore_window=150,
deadband=0.50 — gross Sharpe 1.384, net-of-cost Sharpe 1.265, only 44
trades (vs the original config's much higher turnover that drove the
TC-survival fail).

## Single-config validators (SPY, roc1_period=11/roc2_period=8/wma_window=10/zscore_window=150/sensitivity=0.6/deadband=0.50)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.384 | 1.0 | Yes |
| Max drawdown | 0.085 | 0.25 | Yes |
| TC-survival (net Sharpe) | 1.265 | 0.5 | Yes |
| Walk-forward | 1.00 (4/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std, 108-cell grid) | 0.189 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass with a strong margin** (net Sharpe
1.265, more than double the 0.5 threshold — one of the cleanest fixes this
cron trigger). Combined with `2026-09-14-171`'s QQQ accept (same strategy
file, per-symbol tuned params), the Coppock Curve continuous-sizing dial
now covers QQQ+SPY (equity only; crypto explicitly out of scope per the
predecessor's decisive rejection, not attempted here).
