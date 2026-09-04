# Backtest Report: Andean Oscillator Bull/Bear Signal-Line Crossover

**Strategy file:** `strategies/2026-09-05_andean_oscillator_signal_crossover.py`
**Knowledge base id:** 2026-09-05-016

## Hypothesis

Andean Oscillator (alexgrover, 2022, per Alpaca's blog and TradingView's
open-source library): online-algorithm trend indicator built from
recursive exponential envelope extremities of raw and squared
close/open prices, combined into naive-variance-style bull and bear
components. Entry rule (source's own filtered variant): long when the
bull component crosses above the indicator's own EMA signal line; exit
when the bear component overtakes the bull component, or a
max_hold_days time-stop.

Sources: https://www.tradingview.com/script/qWO9h4a9-Andean-Oscillator/
(usage/rule) and https://alpaca.markets/learn/andean-oscillator (exact
recursive formula derivation).

First Andean Oscillator strategy in this repo — a 2022-era online
recursive-envelope-variance construction distinct from all prior
Keltner/Bollinger/classic-MA-crossover strategies already tested.

## Grid test summary (Step 6)

- `param_grid`: `length` in {20, 25, 30}, `signal_length` in {9, 14}, `max_hold_days` in {20, 30}
- `symbols`: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- `vol_regime_splits=3`
- Period: 2019-01-01 to 2026-09-01
- **144 total cells, 30 passed, pass_fraction = 0.208**
- By asset class: equity 30/72, crypto 0/72
- By vol regime: low 24/48, mid 6/48, high 0/48
- Best cell: length=25, signal_length=9, max_hold_days=30, QQQ, low-vol, Sharpe 2.53
- length=20/signal_length=9/max_hold_days=20 passed 2/3 vol-regime cells on BOTH QQQ and SPY

## Single best-config validators (Step 7)

Config: `length=20, signal_length=9, max_hold_days=20`, full sample 2019-01-01 to 2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.986 | 1.186 | ≥ 1.0 | QQQ ❌ (marginal) / SPY ✅ |
| Max drawdown | 0.143 | 0.122 | ≤ 0.25 | ✅ / ✅ |
| Net Sharpe after costs (10bps/trade) | 0.883 | 1.028 | ≥ 0.5 | ✅ / ✅ |
| Num trades | 68 | 64 | — | — |
| Parameter sensitivity (length x signal_length sweep, QQQ, relative_std) | 0.087 | — | ≤ 0.5 | ✅ (very stable) |

An alternate config (`signal_length=14`, otherwise same) was also
checked: it flips the outcome — QQQ passes (Sharpe 1.060) but SPY then
fails narrowly (Sharpe 0.975). A systematic sweep across all 12
`length`/`signal_length`/`max_hold_days` combinations found **no single
shared configuration where both QQQ and SPY jointly pass Sharpe** — the
two symbols see-saw narrowly around the 1.0 threshold depending on
`signal_length`.

`check_walk_forward` not run (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version).

## Outcome: **REJECTED**

Although parameter sensitivity is excellent (relative_std 0.087,
indicating the underlying edge magnitude is very stable across nearby
configs), no single shared parameter setting produces a robust joint
Sharpe pass for both QQQ and SPY simultaneously — each symbol clears the
1.0 threshold only at a different `signal_length` while the other
symbol falls just short at that same setting. This "narrow see-saw
around threshold" pattern is treated as insufficiently robust for
acceptance (distinct from a genuine per-symbol-scoped pass like
2026-09-05-015's SPY-only TTF accept, where SPY passed cleanly at the
SAME config QQQ also mostly passed at, just missing MDD). Crypto
rejected decisively (0/72 grid cells).
