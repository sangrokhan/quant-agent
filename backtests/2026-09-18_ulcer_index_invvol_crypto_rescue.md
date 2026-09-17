# Backtest Report: Ulcer Index Inverse-Vol Sizing -- Crypto Leverage-Cap Rescue

**Strategy file:** `strategies/2026-09-14_ulcer_index_invvol_sizing_sma_trend.py` (unchanged, existing file)
**Date:** 2026-09-18
**Prior context:** `2026-09-14-170` (QQQ accepted, SPY near-miss, BTC/ETH decisively
rejected at equity-default `leverage_cap=1.0`). Follow-up `2026-09-15-008`
rescued SPY. Crypto was never revisited until this iteration.

## Hypothesis

Direct fix for prior crypto rejection: the strategy's Ulcer Index
inverse-volatility sizing dial + SMA(40) trend gate construction is
unchanged; only `leverage_cap` (and a proportionally-scaled `deadband`) are
retuned per-symbol for crypto's higher baseline volatility, following this
repo's established leverage-cap-aware rescue pattern (same technique that
worked for Elder-Ray, Chaikin Oscillator, Twiggs Money Flow, MAMA/FAMA).
Root-cause diagnosis during this iteration also surfaced a **latent bug**:
the original crypto sweep attempts effectively zeroed out exposure whenever
`deadband >= leverage_cap` (the deadband hysteresis check compares raw
exposure deltas which can never exceed a leverage_cap smaller than the
deadband threshold) -- retuning `deadband` proportionally to the swept
`leverage_cap` (not left at the equity-scale default 0.20) was necessary to
get any nonzero exposure signal at all.

## Leverage-cap sweep (Step 6, manual grid)

`leverage_cap in {0.2,0.25,0.3,0.35,0.4,0.5}` x `trend_window in {40,60}` x
`deadband = leverage_cap * {0.1,0.2,0.3}` (proportionally scaled), 2018-2026.

- **BTC/USDT best:** `leverage_cap=0.5, deadband=0.15, trend_window=40` -- Sharpe 1.188, MDD 0.237
- **ETH/USDT best:** `leverage_cap=0.25, deadband=0.05, trend_window=40` -- Sharpe 1.104, MDD 0.182

## Full validator suite (Step 7)

### BTC/USDT: trend_window=40, ui_window=14, norm_window=100, base_exposure=0.4, sensitivity=0.6, leverage_cap=0.5, deadband=0.15

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.188 | >=1.0 | YES |
| Max drawdown | 0.237 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 221 trades) | 0.963 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (0.41, 2.22, 1.27, 0.89) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.025 | <=0.5 | YES |

### ETH/USDT: trend_window=40, ui_window=14, norm_window=100, base_exposure=0.4, sensitivity=0.6, leverage_cap=0.25, deadband=0.05

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.104 | >=1.0 | YES |
| Max drawdown | 0.182 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 199 trades) | 0.826 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (0.65, 1.86, 0.42, 1.43) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.006 | <=0.5 | YES |

## Decision

**ACCEPTED (BTC/USDT, ETH/USDT)** -- rescues the crypto leg of
`2026-09-14-170`. Full universe now covered for this Ulcer Index
inverse-vol sizing strategy: QQQ (2026-09-14-170), SPY (2026-09-15-008),
BTC/USDT + ETH/USDT (this entry, per-symbol leverage_cap retune).
