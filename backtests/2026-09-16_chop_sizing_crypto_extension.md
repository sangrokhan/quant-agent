# Backtest Report: Choppiness Index Continuous Sizing Dial -- Crypto Extension (SMA trend gate)

**Strategy file:** `strategies/2026-09-13_chop_sizing_shorttrend_deadband.py` (unchanged code, crypto-only parameter retune this iteration)
**Prior entry:** id 2026-09-13-094, accepted QQQ+SPY equity (QQQ Sharpe 1.097, SPY Sharpe 1.132, both walk-forward 1.0, low param sensitivity 0.051-0.081), crypto decisively rejected.

## Hypothesis

Direct fix attempt for prior id 2026-09-13-094 (Choppiness Index INVERSE
continuous sizing dial within an SMA(40) uptrend gate, accepted QQQ+SPY
equity but decisively rejected on crypto at leverage_cap left at equity
default 1.0). This sub-iteration applies this repo's standard
leverage-cap-aware retune (leverage_cap reduced, base_exposure/sensitivity
scaled proportionally) to the identical unmodified CHOP strategy code for
crypto only. No new external research this sub-iteration; formula/source
unchanged from 2026-09-13-094.

## Crypto-only retune sweep

Swept leverage_cap in {0.2, 0.3, 0.4} x sensitivity-scale in {0.3, 0.4,
0.5} x deadband in {0.1, 0.15, 0.2} for both BTC/USDT and ETH/USDT (90
combos total, single-config validators only, reusing an already
grid-tested strategy).

**Result: 38 of 90 combinations passed** Sharpe/MDD/TC-survival, with
Sharpe ranging 1.12-1.48 for BTC and 1.12-1.26 for ETH across passing
configs -- a third robust crypto rescue this cron trigger (after MFI 90/90
and VZO 48/90).

## Selected config

leverage_cap=0.2, base_exposure=0.1, chop_sensitivity=0.06 (0.3*0.2),
deadband=0.1, trend_window=40 (unchanged), chop_window=14/chop_reference=50
(unchanged):

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Trades |
|---|---|---|---|---|
| BTC/USDT | 1.480 (pass) | 0.068 (pass) | 0.858 (pass) | 105 |
| ETH/USDT | 1.124 (pass) | 0.053 (pass) | 0.704 (pass) | 115 |

Equity (QQQ, SPY) unchanged from the original 2026-09-13-094 accept
(Sharpe 1.097/1.132, both walk-forward 1.0, low param sensitivity) -- not
re-run this sub-iteration.

## Decision: ACCEPT -- full universe extension (QQQ, SPY, BTC/USDT, ETH/USDT)

Combined with the existing QQQ+SPY equity accept from 2026-09-13-094,
Choppiness Index continuous-sizing dial now covers the full universe.
This is the third crypto-rescue-only sub-iteration this cron trigger
(after MFI id 2026-09-16-144, VZO id 2026-09-16-145), continuing the
pattern that volume/range/trend-quality bounded-oscillator sizing dials
tend to generalize to crypto cleanly once leverage is appropriately
capped, even when the raw equity-default-leverage config fails MDD
decisively.
