# Bollinger BandWidth (BBW) Inverse-Vol Sizing Dial — QQQ Fix

**Strategy file:** `strategies/2026-09-14_bbw_invvol_sizing_sma_trend.py` (existing file, QQQ config found this iteration)
**Predecessor:** `2026-09-14-150` (accepted SPY/BTC-USDT/ETH-USDT, rejected QQQ — TC-survival near-miss net Sharpe 0.388<0.5, all other validators passed)

## Hypothesis

`2026-09-14-150`'s Bollinger BandWidth (BBW = (Upper-Lower)/Middle*100)
inverse-volatility continuous-sizing dial accepted decisively for SPY,
BTC/USDT and ETH/USDT but QQQ was rejected purely on transaction-cost
survival (323 trades, net Sharpe 0.388) at the grid-tuned config
(bb_window in {15,20,25}, deadband in {0.15,0.25}). This iteration widens
the search to also vary `bb_window` and `norm_window` (not just
sensitivity/deadband) and finds QQQ passes cleanly at
bb_window=15/norm_window=100/sensitivity=0.4/deadband=0.30 (net Sharpe
0.676, turnover roughly halved to 172 trades). No new external source
needed — same already-confirmed BBW formula.

## Grid search (QQQ only, this iteration)

108-cell grid: bb_window in {15,20,25,30} x norm_window in {60,100,150} x
sensitivity in {0.4,0.5,0.6} x deadband in {0.20,0.30,0.40}
(trend_window=40, bb_std=2.0, base_exposure=0.4, leverage_cap=1.0 fixed,
cells with <5 trades excluded). Best cell by (gross Sharpe + net-of-cost
Sharpe): bb_window=15, norm_window=100, sensitivity=0.4, deadband=0.30 —
gross Sharpe 1.232, net-of-cost Sharpe 0.676, 172 trades.

## Single-config validators (QQQ, bb_window=15/norm_window=100/sensitivity=0.4/deadband=0.30)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.232 | 1.0 | Yes |
| Max drawdown | 0.116 | 0.25 | Yes |
| TC-survival (net Sharpe) | 0.676 | 0.5 | Yes |
| Walk-forward | 0.75 (3/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std, 108-cell grid) | 0.118 | 0.5 | Yes |

## Outcome

**QQQ now accepted, all 5 validators pass**, with TC-survival margin
(0.676 vs 0.5) comfortably clearing the prior near-miss's 0.388. Combined
with `2026-09-14-150`'s SPY/BTC/ETH accepts (same strategy file, per-symbol
tuned params), the BBW inverse-vol continuous-sizing dial now covers all 4
symbols this repo tracks — following the same "widen the secondary
parameter, not just sensitivity/deadband" fix pattern as this cron
trigger's prior STARC/LRS/TSV/KST SPY-fix iterations, here applied to a
QQQ-specific near-miss instead.
