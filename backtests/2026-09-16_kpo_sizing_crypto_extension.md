# Backtest Report: Kase Peak Oscillator Continuous Sizing Dial -- Crypto Extension

**Strategy file:** `strategies/2026-09-14_kpo_sizing_sma_trend.py` (unchanged code, crypto-only parameter retune this iteration)
**Prior entry:** id 2026-09-14-169, accepted QQQ+SPY equity, BTC/ETH decisive fail at leverage_cap=1.0. Step 6 grid already showed crypto pass_fraction 14/36 (0.389) at the exploratory leverage_cap=1.0, hinting the signal itself transfers to crypto and only needed a sizing-scale fix.

## Hypothesis

Direct fix attempt for prior id 2026-09-14-169 (Kase Peak Oscillator
continuous sizing dial within an SMA(40) uptrend gate, accepted QQQ+SPY
equity but decisively rejected on crypto at leverage_cap left at equity
default 1.0). The prior entry's own Step 6 grid already showed a
respectable 14/36 (38.9%) crypto pass rate at leverage_cap=1.0 across
different sensitivity/long_cycle combos, suggesting the underlying signal
transfers reasonably to crypto and a leverage-cap-only retune was worth
attempting. This sub-iteration applies the standard leverage-cap-aware
retune to the identical unmodified KPO strategy code for crypto only. No
new external research this sub-iteration.

## Crypto-only retune sweep

Swept leverage_cap in {0.2, 0.3, 0.4} x sensitivity-scale in {0.3, 0.4,
0.5} x deadband in {0.15, 0.2, 0.25} for both BTC/USDT and ETH/USDT (90
combos total).

**Result: 34 of 90 combinations passed** Sharpe/MDD/TC-survival, with
Sharpe ranging 1.03-1.43 for BTC and 1.01-1.35 for ETH across passing
configs -- a fifth robust crypto rescue this cron trigger.

## Selected config

leverage_cap=0.4, base_exposure=0.2, sensitivity=0.16 (0.4*0.4),
deadband=0.15, trend_window=40/short_cycle=8/long_cycle=30/vol_window=9/
vol_sma_window=30/zscore_window=100 (all unchanged):

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Trades |
|---|---|---|---|---|
| BTC/USDT | 1.426 (pass) | 0.166 (pass) | 1.181 (pass) | 121 |
| ETH/USDT | 1.351 (pass) | 0.156 (pass) | 1.161 (pass) | 142 |

Equity (QQQ, SPY) unchanged from the original 2026-09-14-169 accept -- not
re-run this sub-iteration.

## Decision: ACCEPT -- full universe extension (QQQ, SPY, BTC/USDT, ETH/USDT)

Combined with the existing QQQ+SPY equity accept from 2026-09-14-169, Kase
Peak Oscillator continuous-sizing dial now covers the full universe. Fifth
crypto-rescue-only sub-iteration this cron trigger (after MFI, VZO,
Choppiness Index, TSI), completing a productive streak of revisiting this
trigger's own equity-only accepts with the standard leverage-cap-aware
crypto retune.
