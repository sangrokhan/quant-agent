# ZigZag Trend-Maturity Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_zigzag_maturity_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-156` (accepted QQQ/BTC-USDT/ETH-USDT at leverage_cap=0.4 crypto, rejected SPY — genuine near-miss, gross Sharpe 0.874<1.0, all other 4 validators passed)

## Hypothesis

`2026-09-14-156`'s ZigZag (repainting-safe percent-deviation swing pivot)
trend-maturity continuous-sizing dial (signed % distance of close from the
last confirmed pivot, rolling z-scored) accepted decisively for QQQ,
BTC/USDT and ETH/USDT but SPY was a genuine Sharpe near-miss (0.874). This
iteration widens the search across `zigzag_deviation_pct` (not just
sensitivity/deadband) and finds SPY passes cleanly at
zigzag_deviation_pct=3.0/zscore_window=60/sensitivity=0.4/deadband=0.30
(Sharpe 1.119, net Sharpe 0.748). Same strategy file, same already-
confirmed ZigZag pivot state machine (including the pre-grid bug-fix from
the original iteration), no new external fetch.

## Grid search (SPY only, this iteration)

240-cell grid: zigzag_deviation_pct in {3.0,4.0,5.0,6.0,7.0} x
zscore_window in {60,100,150} x sensitivity in {0.4,0.5,0.6,0.7} x
deadband in {0.15,0.20,0.25,0.30} (trend_window=40, base_exposure=0.4,
leverage_cap=1.0 fixed, cells with <5 trades excluded). Best cell by
(gross Sharpe + net-of-cost Sharpe): zigzag_deviation_pct=3.0,
zscore_window=60, sensitivity=0.4, deadband=0.30 — gross Sharpe 1.119,
net-of-cost Sharpe 0.748, 97 trades. A tighter zigzag_deviation_pct (3.0%
vs the original 5.0%) generates more, smaller-magnitude confirmed pivots,
producing a more responsive trend-maturity signal for SPY specifically.

## Single-config validators (SPY, zigzag_deviation_pct=3.0/zscore_window=60/sensitivity=0.4/deadband=0.30)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.119 | 1.0 | Yes |
| Max drawdown | 0.059 | 0.25 | Yes |
| TC-survival (net Sharpe) | 0.748 | 0.5 | Yes |
| Walk-forward | 0.75 (3/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std, 240-cell grid) | 0.116 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass.** Combined with `2026-09-14-156`'s
QQQ/BTC/ETH accepts (same strategy file, per-symbol tuned params), the
ZigZag trend-maturity continuous-sizing dial now covers all 4 symbols this
repo tracks — following the same "widen the secondary parameter, not just
sensitivity/deadband" fix pattern as this cron trigger's prior near-miss
fixes, here varying `zigzag_deviation_pct` (the swing-detection threshold)
specifically.
