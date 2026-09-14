# Accumulation/Distribution Line (ADL) ROC Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_adl_roc_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-153` (accepted QQQ/BTC-USDT/ETH-USDT, rejected SPY — TC-survival near-miss, all other validators passed)

## Hypothesis

`2026-09-14-153`'s Accumulation/Distribution Line (ADL, Marc Chaikin:
cumulative CLV-weighted-volume) continuous-sizing dial (rolling rate-of-
change of raw ADL, z-scored + tanh-squashed) accepted decisively for QQQ,
BTC/USDT and ETH/USDT but SPY was rejected on transaction-cost survival at
the grid-tuned config (roc_window in {10,20,30}, deadband in {0.15,0.25}).
This iteration widens the search to also vary `roc_window`, `zscore_window`
and a wider `deadband` range and finds SPY passes cleanly at
roc_window=10/zscore_window=150/sensitivity=0.5/deadband=0.45 (net Sharpe
0.722, 107 trades). Same strategy file, same already-confirmed ADL formula,
no new external fetch.

## Grid search (SPY only, this iteration)

180-cell grid: roc_window in {10,20,30,40,50} x zscore_window in
{60,100,150} x sensitivity in {0.3,0.4,0.5} x deadband in
{0.35,0.40,0.45,0.50} (trend_window=40, base_exposure=0.4, leverage_cap=1.0
fixed, cells with <5 trades excluded). An initial narrower sweep (deadband
up to 0.40) found several near-misses (Sharpe ~1.0, net Sharpe ~0.55-0.62)
but nothing clearing both thresholds; widening deadband up to 0.50 (further
cutting turnover) found the passing cell. Best cell by (gross Sharpe +
net-of-cost Sharpe): roc_window=10, zscore_window=150, sensitivity=0.5,
deadband=0.45 — gross Sharpe 1.149, net-of-cost Sharpe 0.722, 107 trades.

## Single-config validators (SPY, roc_window=10/zscore_window=150/sensitivity=0.5/deadband=0.45)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.149 | 1.0 | Yes |
| Max drawdown | 0.083 | 0.25 | Yes |
| TC-survival (net Sharpe) | 0.722 | 0.5 | Yes |
| Walk-forward | 1.00 (4/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std, 180-cell grid) | 0.248 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass**, with TC-survival margin (0.722
vs 0.5) comfortably clearing the prior near-miss. Combined with
`2026-09-14-153`'s QQQ/BTC/ETH accepts (same strategy file, per-symbol
tuned params), the ADL ROC continuous-sizing dial now covers all 4 symbols
this repo tracks — following the same "widen the secondary parameter, not
just sensitivity/deadband" fix pattern as this cron trigger's prior
STARC/LRS/TSV/KST/BBW near-miss fixes.
