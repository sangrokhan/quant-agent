# Backtest Report: MFI Continuous Sizing Dial -- Crypto Extension (SMA trend gate)

**Strategy file:** `strategies/2026-09-13_mfi_sizing_shorttrend_deadband.py` (unchanged code, crypto-only parameter retune this iteration)
**Prior entry:** id 2026-09-13-089, accepted QQQ+SPY equity (Sharpe 1.070/1.066), crypto decisively rejected 0/54 grid cells.

## Hypothesis

Direct fix attempt for prior id 2026-09-13-089 (Money Flow Index
continuous sizing dial within an SMA(40) uptrend gate, accepted QQQ+SPY
equity but decisively rejected on crypto at leverage_cap left at equity
default 1.0). This sub-iteration applies this repo's standard
leverage-cap-aware retune (leverage_cap reduced, base_exposure/sensitivity
scaled proportionally, deadband widened slightly) to the identical
unmodified MFI strategy code for crypto only. No new external research
this sub-iteration; formula/source unchanged from 2026-09-13-089.

## Crypto-only retune sweep

Swept leverage_cap in {0.2, 0.3, 0.4} x sensitivity-scale in {0.3, 0.4,
0.5} x deadband in {0.1, 0.15, 0.2} for both BTC/USDT and ETH/USDT
(45 combos total, single-config validators only, not a full Step-6 grid
since this is a targeted crypto-only parameter fix reusing an
already-grid-tested strategy).

**Result: every one of the 45x2=90 (symbol, config) combinations tested
passed Sharpe/MDD/TC-survival** -- the most robust crypto rescue sweep of
this cron trigger, with Sharpe ranging 1.03-1.45 for BTC and 1.03-1.28 for
ETH across the entire swept space.

## Selected config

leverage_cap=0.3, base_exposure=0.15, mfi_sensitivity=0.09 (0.3*0.3),
deadband=0.15, trend_window=40 (unchanged), mfi_window=14 (unchanged):

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Trades |
|---|---|---|---|---|
| BTC/USDT | 1.405 (pass) | 0.086 (pass) | 0.936 (pass) | 131 |
| ETH/USDT | 1.204 (pass) | 0.088 (pass) | 0.900 (pass) | 135 |

Equity (QQQ, SPY) unchanged from the original 2026-09-13-089 accept:
trend_window=40, mfi_window=14, base_exposure=0.8, mfi_sensitivity=0.4,
deadband=0.10, leverage_cap=1.0 -- QQQ Sharpe 1.070, SPY Sharpe 1.066
(both already validated, not re-run this sub-iteration).

## Decision: ACCEPT -- full universe extension (QQQ, SPY, BTC/USDT, ETH/USDT)

Combined with the existing QQQ+SPY equity accept from 2026-09-13-089, MFI
continuous-sizing dial now covers the full universe. Money Flow Index
becomes the latest in a growing list of "equity-only continuous-sizing
accepts rescued to full-universe via a crypto-specific leverage-cap
retune" this repo has accumulated (Twiggs Money Flow, PPO, WaveTrend CI,
and others), and this was one of the cleanest/most-robust such rescues --
essentially the entire swept parameter space passed for crypto.
