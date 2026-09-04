# Backtest Report: Ehlers Roofing Filter SMA-Signal-Line Crossover + Trend Filter

**Strategy file:** `strategies/2026-09-05_roofing_filter_signal_crossover.py`
**Knowledge base id:** 2026-09-05-012

## Hypothesis

John Ehlers' Roofing Filter (2-pole highpass filter removing cycles >
highpass_period bars, then a SuperSmoother lowpass removing noise <
lowpass_period bars) hugs price with less lag/jitter than a comparable
EMA. Concrete rule (per theindicatorlab.com): long entry when the Roofing
Filter line crosses above its own 3-period SMA signal line, gated by
close above a 200-EMA trend filter; exit on the reverse crossover or
price closing below the filter line.

Sources:
https://theindicatorlab.com/reviews/ehlers-roofing-filter-review-settings-strategy-and-how-to-use-it
(trading rule) and
https://www.prorealcode.com/prorealtime-indicators/my-stochastic-oscillator-john-ehlers/
(exact HP+SuperSmoother coefficient formula, transcribed from Ehlers'
own EasyLanguage code).

First strategy in this repo using the Roofing Filter directly as a
trend-following SMA-crossover signal — distinct from MESA Stochastic
(id=2026-09-04-118, already rejected), which converts the SAME
underlying HP+SuperSmoother "Filt" construction into a bounded 0-1
countertrend oscillator instead.

## Grid test summary (Step 6)

- `param_grid`: `highpass_period` in {40, 48}, `lowpass_period` in {10, 14}, `max_hold_days` in {20, 30}
- `symbols`: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- `vol_regime_splits=3`
- Period: 2019-01-01 to 2026-09-01
- **96 total cells, 18 passed, pass_fraction = 0.1875**
- By asset class: equity 18/48, crypto 0/48
- By vol regime: low 12/32, mid 6/32, high 0/32
- Best cell: highpass=40, lowpass=10, max_hold_days=20, SPY, low-vol, Sharpe 2.26
- QQQ's best param combo (highpass=48, lowpass=14) passed 2/3 vol-regime cells

## Single best-config validators (Step 7)

Config: `highpass_period=48, lowpass_period=14, max_hold_days=20`, full sample 2019-01-01 to 2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.768 | 0.508 | ≥ 1.0 | ❌ / ❌ |
| Max drawdown | 0.182 | 0.142 | ≤ 0.25 | ✅ / ✅ |
| Net Sharpe after costs (10bps/trade) | 0.560 | 0.270 | ≥ 0.5 | ✅ / ❌ |
| Num trades | 123 | 116 | — | high trade frequency |
| Parameter sensitivity (highpass x lowpass sweep, QQQ, relative_std) | 0.236 | — | ≤ 0.5 | ✅ (passes, but moot given Sharpe fail) |

`check_walk_forward` not run (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version).

## Outcome: **REJECTED**

Full-sample Sharpe decisively fails on both QQQ (0.768) and SPY (0.508)
against the 1.0 threshold, despite the grid's isolated low/mid-vol-tercile
passes (best cell Sharpe 2.26). Parameter sensitivity is actually fine
(relative_std 0.236, well under 0.5) — this is NOT an overfitting
problem, but simply an edge too weak to survive full-sample averaging
with high trade frequency (123/116 trades over 7.5yr) diluting the
isolated-regime gains. Crypto rejected decisively (0/48 grid cells).
