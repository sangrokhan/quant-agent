# STARC %B Continuous Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_starc_pctb_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-144` (accepted QQQ/BTC/USDT/ETH/USDT, rejected SPY — TC-survival near-miss, net Sharpe 0.385<0.5, all other 4 validators passed)

## Hypothesis

`2026-09-14-144`'s STARC Bands %B continuous-sizing dial accepted
decisively for QQQ, BTC/USDT, and ETH/USDT but SPY was rejected purely on
transaction-cost-survival (net Sharpe 0.385 vs 0.5 threshold, at QQQ's
tuned config sensitivity=0.6/deadband=0.2, 440 trades over the full
sample) — every other validator passed. This iteration searches a wider
sensitivity/deadband combination specifically for SPY and finds
sensitivity=0.4/deadband=0.35 clears TC-survival (turnover roughly halved
to 170 trades) while keeping Sharpe above 1.0. No new external source
needed — same already-confirmed STARC Bands formula.

## Single-config validators (SPY, sensitivity=0.4/deadband=0.35)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.033 | 1.0 | Yes |
| Max drawdown | 0.069 | 0.25 | Yes |
| TC-survival (net Sharpe) | 0.546 | 0.5 | Yes |
| Walk-forward | 1.00 (4/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std) | 0.061 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass.** Combined with `2026-09-14-144`'s
QQQ/BTC/ETH accepts (same strategy file, per-symbol tuned params), the
STARC Bands %B continuous-sizing dial now covers all 4 symbols this repo
tracks, at these per-symbol configs:
- QQQ: sensitivity=0.6, deadband=0.2
- SPY (this entry): sensitivity=0.4, deadband=0.35
- BTC/USDT, ETH/USDT: leverage_cap=0.4 (per predecessor entry)
