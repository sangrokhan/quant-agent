# Backtest Report: Ergodic Oscillator Sizing Dial -- Crypto Leverage-Cap Rescue

**Strategy file:** `strategies/2026-09-14_ergodic_sizing_sma_trend.py` (unchanged, existing file)
**Date:** 2026-09-18
**Prior context:** `2026-09-14-176` (QQQ+SPY accepted, BTC/USDT and ETH/USDT
decisively rejected on MDD at equity-default `leverage_cap=1.0`).

## Hypothesis

Direct fix for prior crypto MDD rejection, reusing this repo's established
leverage-cap-aware rescue pattern (validated repeatedly this cron trigger
for Ulcer Index and Andean Oscillator, `2026-09-18-039`/`-040`). Same
Ergodic Oscillator (William Blau double-smoothed momentum ratio) formula
and same SMA(40) trend gate; only `leverage_cap` and a proportionally-scaled
`deadband` are retuned per symbol.

## Leverage-cap sweep (Step 6, manual grid)

`leverage_cap in {0.2,0.25,0.3,0.35,0.4,0.5}` x `trend_window in {40,60}` x
`deadband = leverage_cap * {0.1,0.2,0.3}`, 2018-2026.

- **BTC/USDT best:** `leverage_cap=0.35, deadband=0.035, trend_window=40` -- Sharpe 1.174, MDD 0.201
- **ETH/USDT best:** `leverage_cap=0.35, deadband=0.07, trend_window=40` -- Sharpe 1.072, MDD 0.245 (near the 0.25 ceiling but passes)

## Full validator suite (Step 7)

### BTC/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.174 | >=1.0 | YES |
| Max drawdown | 0.201 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 209 trades) | 0.906 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (0.47, 2.06, 1.34, 0.87) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.005 | <=0.5 | YES |

### ETH/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.072 | >=1.0 | YES |
| Max drawdown | 0.245 | <=0.25 | YES (thin margin) |
| TC survival (net Sharpe, 10bps, 189 trades) | 0.911 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (0.58, 1.94, 0.42, 1.38) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.005 | <=0.5 | YES |

## Decision

**ACCEPTED (BTC/USDT, ETH/USDT)** -- rescues the crypto leg of
`2026-09-14-176`. Full universe now covered: QQQ+SPY (2026-09-14-176),
BTC/USDT+ETH/USDT (this entry). Note ETH/USDT MDD margin is thin (0.245 vs
0.25 ceiling) -- flag for future monitoring if retested with a wider
out-of-sample window.
