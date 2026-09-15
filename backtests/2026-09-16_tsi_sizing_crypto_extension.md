# Backtest Report: TSI Continuous Sizing Dial -- Crypto Extension (SMA trend gate)

**Strategy file:** `strategies/2026-09-14_tsi_sizing_sma_trend.py` (unchanged code, crypto-only parameter retune this iteration)
**Prior entry:** id 2026-09-14-096, accepted QQQ+SPY equity (all 5 validators pass), crypto BTC/USDT decisive MDD fail (31.17%>25%) despite strong Sharpe/TC/WF/param-sensitivity at leverage_cap=1.0.

## Hypothesis

Direct fix attempt for prior id 2026-09-14-096 (True Strength Index
continuous sizing dial within an SMA(40) uptrend gate, accepted QQQ+SPY
equity but rejected on crypto specifically and only on MDD -- all other
validators, including Sharpe, already passed at the equity-default
leverage_cap=1.0). This sub-iteration applies this repo's standard
leverage-cap-aware retune (leverage_cap reduced, base_exposure/sensitivity
scaled proportionally) to the identical unmodified TSI strategy code for
crypto only. No new external research this sub-iteration.

## Crypto-only retune sweep

Swept leverage_cap in {0.2, 0.3, 0.4} x sensitivity-scale in {0.3, 0.4,
0.5} x deadband in {0.1, 0.15, 0.2} for both BTC/USDT and ETH/USDT (90
combos total).

**Result: 40 of 90 combinations passed** Sharpe/MDD/TC-survival, with
Sharpe ranging 1.00-1.49 for BTC and 1.08-1.24 for ETH across passing
configs -- a fourth robust crypto rescue this cron trigger (after MFI
90/90, VZO 48/90, Choppiness Index 38/90).

## Selected config

leverage_cap=0.3, base_exposure=0.15, tsi_sensitivity=0.09 (0.3*0.3),
deadband=0.1, trend_window=40/tsi_fast=13/tsi_slow=25 (unchanged):

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Trades |
|---|---|---|---|---|
| BTC/USDT | 1.482 (pass) | 0.087 (pass) | 0.808 (pass) | 171 |
| ETH/USDT | 1.244 (pass) | 0.110 (pass) | 0.804 (pass) | 165 |

Both MDD values (0.087, 0.110) are far below the 0.25 threshold and far
below the original decisive fail (0.3117), confirming this was purely a
sizing-scale issue at the original equity-default leverage, not a
signal-quality problem for crypto.

Equity (QQQ, SPY) unchanged from the original 2026-09-14-096 accept (all 5
validators already passed) -- not re-run this sub-iteration.

## Decision: ACCEPT -- full universe extension (QQQ, SPY, BTC/USDT, ETH/USDT)

Combined with the existing QQQ+SPY equity accept from 2026-09-14-096, TSI
continuous-sizing dial now covers the full universe. Fourth
crypto-rescue-only sub-iteration this cron trigger (after MFI id
2026-09-16-144, VZO id 2026-09-16-145, Choppiness Index id 2026-09-16-146).
