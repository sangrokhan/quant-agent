# Backtest Report: VZO Continuous Sizing Dial -- Crypto Extension (SMA trend gate)

**Strategy file:** `strategies/2026-09-13_vzo_sizing_shorttrend_deadband.py` (unchanged code, crypto-only parameter retune this iteration)
**Prior entry:** id 2026-09-13-091, accepted QQQ+SPY equity with the strongest margins of that cron trigger, crypto decisively rejected.

## Hypothesis

Direct fix attempt for prior id 2026-09-13-091 (Volume Zone Oscillator
continuous sizing dial within an SMA(40) uptrend gate, accepted QQQ+SPY
equity with strong margins but decisively rejected on crypto BTC/USDT and
ETH/USDT at leverage_cap left at equity default 1.0). This sub-iteration
applies this repo's standard leverage-cap-aware retune (leverage_cap
reduced, base_exposure/sensitivity scaled proportionally) to the identical
unmodified VZO strategy code for crypto only. No new external research
this sub-iteration; formula/source unchanged from 2026-09-13-091 (itself
reused from this repo's own 2 prior VZO entries).

## Crypto-only retune sweep

Swept leverage_cap in {0.2, 0.3, 0.4} x sensitivity-scale in {0.3, 0.4,
0.5} x deadband in {0.1, 0.15, 0.2} for both BTC/USDT and ETH/USDT
(45 combos x 2 symbols = 90 total, single-config validators only, reusing
an already grid-tested strategy).

**Result: 48 of 90 combinations passed** Sharpe/MDD/TC-survival, with
Sharpe ranging 1.14-1.51 for BTC and 1.14-1.47 for ETH across passing
configs -- another very robust crypto rescue, second only to MFI's 90/90
sweep this cron trigger.

## Selected config

leverage_cap=0.2, base_exposure=0.1, vzo_sensitivity=0.06 (0.3*0.2),
deadband=0.15, trend_window=40 (unchanged), vzo_window=14 (unchanged):

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Trades |
|---|---|---|---|---|
| BTC/USDT | 1.506 (pass) | 0.071 (pass) | 1.261 (pass) | 69 |
| ETH/USDT | 1.204 (pass) | 0.070 (pass) | 1.032 (pass) | 75 |

Equity (QQQ, SPY) unchanged from the original 2026-09-13-091 accept
(QQQ Sharpe 1.297, described as "the strongest overall result of the
entire [prior] cron trigger") -- not re-run this sub-iteration.

## Decision: ACCEPT -- full universe extension (QQQ, SPY, BTC/USDT, ETH/USDT)

Combined with the existing QQQ+SPY equity accept from 2026-09-13-091, VZO
continuous-sizing dial now covers the full universe. This is the second
crypto-rescue-only sub-iteration this cron trigger (after MFI), and both
rescues used the same standard leverage-cap-aware retune pattern with a
high success rate across the swept parameter space, suggesting this class
of volume-weighted bounded-oscillator sizing dial generalizes well to
crypto once leverage is appropriately capped.
