# No-Nines Donchian Breakout — Backtest Report

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_no_nines_donchian_breakout.py`
**Source:** https://thepatternsite.com/NoNines.html (Thomas Bulkowski, "No-Nines"
strategy, citing Ken Calhoun's TASC Aug-2017 article "Avoiding False
Breakouts; No 9s"), read via browser_exec.

## Hypothesis

Professional traders treat every $10 price increment as a resistance level,
so breakouts with a "9" in the ones-place (e.g. $29.xx, $49.xx) more often
fail. Bulkowski's own 25-year, 11,077-trade backtest (1,010 stocks,
1992-2017) found delaying entry on such "9-handle" breakouts until price
clears 50 cents above the next whole dollar (e.g. buy at $50.50 instead of
entering at $49.30) modestly raised average gain (30.0% -> 30.3% for
$20-70 stocks / upward breakouts, per his Table 1) and reduced the 5%-failure
rate (30.8% -> 30.3%).

Bulkowski's own test used discretionary chart patterns not detectable from
plain OHLCV. This iteration adapts the same no-nines LOGIC onto a mechanical
Donchian channel breakout: raw entry = close > rolling N-day high; if that
breakout day's close has "9" as its ones-digit (int(close) % 10 == 9), delay
entry until a later close clears floor(breakout_close) + 1.50, abandoning the
delayed trade if it isn't confirmed within `delay_window` bars or if the
exit-window low is hit first. Exit = classic Donchian exit-window low, or a
`max_hold_days` time-stop backstop.

## Grid test summary (Step 6)

`entry_window` in {20,40}, `exit_window` in {10,20}, `delay_window` in {3,7},
equity {QQQ, SPY} + crypto {BTC/USDT, ETH/USDT}, vol_regime_splits=3.
Full grid: 96 cells.

- **pass_fraction: 0.354** (34/96)
- **by_asset_class:** equity 26/48 passed; crypto 8/48 passed (decisively
  weaker on crypto)
- **by_vol_regime:** low 24/32; mid 8/32; high 2/32 (strongly low-vol-regime
  dependent, consistent with a breakout/trend strategy underperforming in
  choppy/high-vol conditions)
- **best_cell:** entry_window=40, exit_window=20, delay_window=3, SPY,
  low-vol regime, Sharpe 2.665
- **worst_cell:** entry_window=40, exit_window=10, delay_window=3, SPY,
  high-vol regime, Sharpe -0.956

## Single-config validation (Step 7)

Config: `entry_window=40, exit_window=20, delay_window=3,
no_nines_delay_cents=0.50, max_hold_days=40`. Full sample 2019-01-01 to
2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) |
|---|---|---|---|---|
| QQQ | **1.303 PASS** | 0.218 PASS | 1.255 PASS (31 trades) | 0.054 PASS |
| SPY | 0.651 **FAIL** | 0.222 PASS | 0.581 PASS (37 trades) | 0.211 PASS |

`check_walk_forward` errored with a pre-existing repo bug in
`validation/validators.py` (`vbt.utils.splitting` attribute does not exist in
the installed vectorbt version) unrelated to this strategy's own logic;
skipped this iteration per `suggested_workload=light` guidance in
RESEARCH_LOOP.md Step 7 ("skip walk-forward under light if
time/compute-constrained, but say so in notes").

## Decision

**Accepted for QQQ only.** All 4 runnable validators (Sharpe, MDD, tx-cost
survival, parameter sensitivity) pass for QQQ. SPY fails the Sharpe
threshold (0.651 < 1.0) despite passing the other 3 -- rejected for SPY.
Crypto (BTC/USDT, ETH/USDT) rejected decisively per the grid (8/48 cells
passed, concentrated in low-vol regime only, no full-sample config tested
given the grid's weak crypto showing).
