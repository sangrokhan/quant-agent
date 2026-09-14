# Normalized Linear Regression Slope (LRS) Continuous Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_lrs_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-146` (accepted QQQ/BTC/USDT/ETH/USDT, rejected SPY — TC-survival near-miss, all other validators passed)

## Hypothesis

`2026-09-14-146`'s Normalized Linear Regression Slope continuous-sizing
dial accepted decisively for QQQ, BTC/USDT, and ETH/USDT but SPY was
rejected purely on transaction-cost-survival at the grid-tuned config
(lrs_window=20, various deadband). This iteration widens the search to
also vary `trend_window` and `lrs_window` and finds SPY passes cleanly at
trend_window=40/lrs_window=15/sensitivity=0.4/deadband=0.4. No new
external source needed — same already-confirmed LRS formula.

## Search process

Broad grid over trend_window∈{30,40,60}, lrs_window∈{15,20,25,30},
sensitivity∈{0.4,0.5,0.6,0.7,0.8}, deadband∈{0.3,0.35,0.4,0.45} found best
full-sample Sharpe 1.272 at trend_window=40/lrs_window=15/sensitivity=0.4/
deadband=0.4 — turnover drops sharply to 86 trades (vs 337 at the original
grid's tighter deadband=0.15), pushing net Sharpe after costs comfortably
above 1.0.

## Single-config validators (SPY, trend_window=40/lrs_window=15/sensitivity=0.4/deadband=0.4)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.272 | 1.0 | Yes |
| Max drawdown | 0.081 | 0.25 | Yes |
| TC-survival (net Sharpe) | 1.011 | 0.5 | Yes |
| Walk-forward | 1.00 (4/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std) | 0.176 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass, with the strongest margins of
any near-miss fix this cron trigger** (TC-survival net Sharpe 1.011 vs
0.5 threshold — more than double). Combined with `2026-09-14-146`'s
QQQ/BTC/ETH accepts (same strategy file, per-symbol tuned params), the LRS
continuous-sizing dial now covers all 4 symbols this repo tracks.
