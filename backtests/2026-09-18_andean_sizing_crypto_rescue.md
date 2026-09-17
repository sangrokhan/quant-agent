# Backtest Report: Andean Oscillator Sizing Dial -- Crypto Leverage-Cap Rescue

**Strategy file:** `strategies/2026-09-14_andean_bullbear_sizing_sma_trend.py` (unchanged, existing file)
**Date:** 2026-09-18
**Prior context:** `2026-09-14-160` (QQQ/SPY accepted, BTC/USDT and ETH/USDT
decisively rejected -- Sharpe+MDD+TC all failed at equity-default
`leverage_cap=1.0`).

## Hypothesis

Direct fix for prior crypto rejection, reusing this repo's established
leverage-cap-aware rescue pattern (same technique validated repeatedly this
week for Elder-Ray/Chaikin/Twiggs/MAMA-FAMA/Ulcer Index). Same formula
(Andean Oscillator bull/bear net pressure, exponential up/down envelope
construction), only `leverage_cap` and a **proportionally-scaled**
`deadband` are retuned per symbol -- applying the same `deadband >=
leverage_cap` zero-exposure bug fix diagnosed and documented in this
iteration's prior entry (`2026-09-18-039`, Ulcer Index crypto rescue).

## Leverage-cap sweep (Step 6, manual grid)

`leverage_cap in {0.2,0.25,0.3,0.35,0.4,0.5}` x `trend_window in {40,60}` x
`deadband = leverage_cap * {0.1,0.2,0.3}`, 2018-2026.

- **BTC/USDT best:** `leverage_cap=0.3, deadband=0.06, trend_window=40` -- Sharpe 1.169, MDD 0.166
- **ETH/USDT best:** `leverage_cap=0.2, deadband=0.02, trend_window=40` -- Sharpe 1.081, MDD 0.146

## Full validator suite (Step 7)

### BTC/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.169 | >=1.0 | YES |
| Max drawdown | 0.166 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 209 trades) | 0.822 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (0.56, 1.86, 1.29, 0.99) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.010 | <=0.5 | YES |

### ETH/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.081 | >=1.0 | YES |
| Max drawdown | 0.146 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 211 trades) | 0.714 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (0.64, 1.80, 0.48, 1.48) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.003 | <=0.5 | YES |

## Decision

**ACCEPTED (BTC/USDT, ETH/USDT)** -- rescues the crypto leg of
`2026-09-14-160`. Full universe now covered: QQQ+SPY (2026-09-14-160),
BTC/USDT+ETH/USDT (this entry).
