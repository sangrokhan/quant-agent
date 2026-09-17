# Backtest Report: Kairi Relative Index (range-position) Sizing Dial -- Crypto Leverage-Cap Rescue

**Strategy file:** `strategies/2026-09-14_kri_rangepos_sizing_sma_trend.py` (unchanged, existing file)
**Date:** 2026-09-18
**Prior context:** `2026-09-14-180` (QQQ+SPY accepted with strong margins,
BTC/USDT and ETH/USDT decisively rejected on MDD at equity-default
`leverage_cap=1.0`).

## Hypothesis

Direct fix for prior crypto MDD rejection, reusing this cron trigger's
leverage-cap-aware rescue pattern (5th application this trigger, after
Ulcer Index/Andean/Ergodic/PVO). Same range-position Kairi Relative Index
formula (`KRI=((Close-Low)-(High-Close))/(High-Low)*100`, bounded
[-100,+100]) and SMA(trend_window) trend gate; `leverage_cap`, `period`,
`trend_window`, and `deadband` retuned per symbol.

## Sweep summary (Step 6, manual grid)

`leverage_cap in {0.15..0.4}` x `trend_window in {30,40,60}` x
`period in {10,14,21}` x `deadband = leverage_cap*{0.1..0.4}`, 2018-2026,
jointly checking Sharpe/MDD/TC-survival this time (learning from the PVO
rescue's two-pass lesson).

- **BTC/USDT best:** trend_window=60, period=14, leverage_cap=0.4, deadband=0.04 -- Sharpe 1.232, MDD 0.206
- **ETH/USDT best:** trend_window=40, period=14, leverage_cap=0.25, deadband=0.10 -- Sharpe 1.144, MDD 0.172

## Full validator suite (Step 7)

### BTC/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.232 | >=1.0 | YES |
| Max drawdown | 0.206 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 425 trades) | 0.645 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (0.90, 1.75, 0.93, 1.38) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.014 | <=0.5 | YES |

### ETH/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.144 | >=1.0 | YES |
| Max drawdown | 0.172 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 260 trades) | 0.751 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (0.68, 2.26, 0.53, 1.15) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.012 | <=0.5 | YES |

## Decision

**ACCEPTED (BTC/USDT, ETH/USDT)** -- rescues the crypto leg of
`2026-09-14-180`. Full universe now covered: QQQ+SPY (2026-09-14-180),
BTC/USDT+ETH/USDT (this entry).
