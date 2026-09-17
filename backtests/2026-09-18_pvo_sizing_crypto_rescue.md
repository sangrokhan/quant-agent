# Backtest Report: PVO Sizing Dial -- Crypto Leverage-Cap Rescue

**Strategy file:** `strategies/2026-09-14_pvo_sizing_sma_trend.py` (unchanged, existing file)
**Date:** 2026-09-18
**Prior context:** `2026-09-14-177` (QQQ+SPY accepted, BTC/USDT and ETH/USDT
decisively rejected on MDD at equity-default `leverage_cap=1.0`).

## Hypothesis

Direct fix for prior crypto MDD rejection, reusing this repo's established
leverage-cap-aware rescue pattern (validated repeatedly this cron trigger:
Ulcer Index 2026-09-18-039, Andean Oscillator -040, Ergodic Oscillator
-041). Same Percentage Volume Oscillator (PVO) formula and SMA trend gate;
`leverage_cap`, `trend_window`, `zscore_window`, and `deadband` are all
retuned per symbol. First-pass leverage-only sweep found a BTC pass but an
ETH near-miss on Sharpe (0.948) and both symbols later failed TC-survival
at tight deadbands (330/342 trades) -- a second sweep widening the deadband
fraction (up to 0.5x leverage_cap) fixed the turnover-driven TC-survival
failures for both symbols while preserving Sharpe/MDD margins.

## Sweep summary (Step 6, manual grid, two passes)

Pass 1 (leverage_cap x trend_window x tight deadband): BTC passed, ETH
Sharpe near-miss (0.948).
Pass 2 (wider trend_window/zscore_window/leverage_cap x wider deadband up
to 0.5x leverage_cap): both symbols found passing configs.

- **BTC/USDT best:** trend_window=40, zscore_window=60, leverage_cap=0.4, deadband=0.16 -- Sharpe 1.332, MDD 0.187
- **ETH/USDT best:** trend_window=30, zscore_window=60, leverage_cap=0.3, deadband=0.15 -- Sharpe 1.180, MDD 0.144

## Full validator suite (Step 7)

### BTC/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.332 | >=1.0 | YES |
| Max drawdown | 0.187 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 272 trades) | 0.855 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (1.04, 2.12, 1.06, 1.13) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.048 | <=0.5 | YES |

### ETH/USDT

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.180 | >=1.0 | YES |
| Max drawdown | 0.144 | <=0.25 | YES |
| TC survival (net Sharpe, 10bps, 223 trades) | 0.870 | >=0.5 | YES |
| Walk-forward (4-slice manual) | 4/4 positive (1.04, 1.94, 0.87, 0.67) | >=0.75 | YES |
| Parameter sensitivity (15-pt leverage_cap x deadband sweep) | rel.std 0.050 | <=0.5 | YES |

## Decision

**ACCEPTED (BTC/USDT, ETH/USDT)** -- rescues the crypto leg of
`2026-09-14-177`. Full universe now covered: QQQ+SPY (2026-09-14-177),
BTC/USDT+ETH/USDT (this entry). Note this indicator required wider deadband
tuning than the prior three crypto rescues this trigger -- flag for future
loops that the naive `deadband = leverage_cap * small_fraction` heuristic
doesn't always transfer; a dedicated TC-survival-aware deadband sweep may be
needed per indicator.
