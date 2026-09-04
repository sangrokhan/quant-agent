# 2026-09-04 RVOL-Confirmed N-Day-High Breakout — Backtest Report

**Hypothesis** (id `2026-09-04-166`): A close breaking above a rolling N-day
high is a higher-conviction long entry when confirmed by a relative-volume
(RVOL = volume / rolling avg volume) spike >= 1.5x at the breakout bar,
signalling genuine institutional participation. Per Nydar's volume-analysis
snippet ("Buy when price breaks resistance on 50%+ above-average volume" =
RVOL>=1.5x) and onetradejournal's RVOL bucket table (1.5-2.0x = stronger
breakout signal).

**Sources**: https://nydar.co.uk/learn/volume-analysis-indicators-and-strategies
(404, rule captured from Google snippet); https://onetradejournal.com/volume-breakout-strategy-india-rvol-rules/
(404, rule captured from Google snippet)

**Strategy**: `strategies/2026-09-04_rvol_breakout_confirmation.py`

## Grid test (breakout_window∈{20,40}, rvol_threshold∈{1.5,2.0}, max_hold_days∈{15,20}; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 96, passed_cells: 8, **pass_fraction: 8.3%**
- by_asset_class: equity 8/48 passed; crypto 0/48
- by_vol_regime: low 8/32, mid 0/32, high 0/32 (low-vol-only)

## Single-config validation, full sample 2019-2026 (breakout_window=20, rvol_threshold=1.5, max_hold_days=20)

| Symbol | Sharpe | Passed | MDD | ~Trades |
|---|---|---|---|---|
| QQQ | 1.090 | YES | 0.015 | **4** |
| SPY | 0.328 | NO | 0.072 | (not counted, decisive miss) |

QQQ's Sharpe passes numerically (1.09) but on only **4 total trades** across
the entire 2019-2026 sample -- statistically meaningless (a Sharpe ratio
computed from 4 trades carries essentially no信頼性; the RVOL>=1.5x AND
N-day-high-breakout joint condition is far too rare an event to trust).
Transaction-cost survival and parameter-sensitivity technically "passed"
but are equally unreliable given the tiny sample. SPY fails decisively
(0.328). Crypto 0/48 grid cells.

## Decision: REJECTED

Rejected on both grounds: (1) SPY fails decisively at the shared config,
and (2) QQQ's apparent pass is an artifact of an extremely sparse signal
(4 trades in 7.5 years) rather than a genuine statistically meaningful
edge. The RVOL confirmation filter combined with a 20-day breakout is too
restrictive a joint condition to produce a testable strategy at daily-bar
frequency -- volume spikes at the exact moment of a 20-day-high breakout
are rare events. A future loop could retry with a looser breakout lookback
or RVOL threshold to get a more statistically meaningful trade count before
concluding either way on the underlying idea.
