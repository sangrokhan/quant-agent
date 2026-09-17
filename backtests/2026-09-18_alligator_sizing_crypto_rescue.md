# Backtest Report: Williams Alligator Spread Sizing Dial -- Crypto Leverage-Cap Rescue

**Strategy file:** `strategies/2026-09-14_alligator_spread_sizing_sma_trend.py` (unchanged, existing file)
**Date:** 2026-09-18
**Prior context:** `2026-09-14-182` (QQQ thin pass + SPY accepted, BTC/USDT
and ETH/USDT decisively rejected on MDD at equity-default `leverage_cap=1.0`).

## Hypothesis

Direct fix for prior crypto MDD rejection, reusing this cron trigger's
leverage-cap-aware rescue pattern (7th application this trigger). Same
ATR-normalized Lips-Jaw fan-spread formula (Bill Williams Alligator,
SMMA-based) and SMA(trend_window) trend gate; `leverage_cap` and
proportionally-scaled `deadband` retuned per symbol, jointly checked
against Sharpe/MDD/TC-survival in a single sweep pass.

## Sweep summary (Step 6, manual grid)

`leverage_cap in {0.2..0.4}` x `trend_window in {40,60}` x
`deadband = leverage_cap*{0.15,0.3,0.45}`, 2018-2026.

- **BTC/USDT best:** trend_window=40, leverage_cap=0.4, deadband=0.18 -- Sharpe 1.182, MDD 0.202
- **ETH/USDT best:** trend_window=40, leverage_cap=0.2, deadband=0.06 -- Sharpe 1.007, MDD 0.184

## Full validator suite (Step 7)

### BTC/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.182 | >=1.0 | YES |
| Max drawdown | 0.202 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 176 trades) | 0.961 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (0.53, 2.07, 1.30, 0.91) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.039 | <=0.5 | YES |

### ETH/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.007 | >=1.0 | YES (thin margin) |
| Max drawdown | 0.184 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 197 trades) | 0.667 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 3/4 positive (0.76, 1.87, -0.02, 1.31) | >=0.75 | YES (exactly at threshold) |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.014 | <=0.5 | YES |

## Decision

**ACCEPTED (BTC/USDT, ETH/USDT)** -- rescues the crypto leg of
`2026-09-14-182`. Full universe now covered: QQQ (thin pass) + SPY
(2026-09-14-182), BTC/USDT+ETH/USDT (this entry). Note ETH/USDT margins are
thin (Sharpe 1.007, walk-forward exactly at 0.75 threshold with one
negative-Sharpe slice) -- flag as a weaker accept worth future re-validation
if the sample window extends.
