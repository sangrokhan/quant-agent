# Backtest Report: Q4-Seasonal-Gated BTC Donchian Breakout (2026-09-26)

**Strategy file:** `strategies/2026-09-26_q4_seasonal_btc_donchian_breakout.py`
**KB id:** 2026-09-26-012

## Hypothesis

Per VoiceOfChain's "Crypto Seasonality Strategy: Rules Traders Can Use"
(https://voiceofchain.com/academy/crypto-seasonality-strategy, free
disclosed rule): Q4 (Oct-Dec) is historically the strongest risk-on
seasonal window for BTC. Source's own disclosed rules-based breakout
setup: only trade long in the seasonal window AND when BTC is above its
50-day MA; entry on a daily close above the rolling 20-day high; stop
below the breakout candle's low or 1.5x daily ATR; trail the remainder
below the 10-day EMA. First calendar-gated (Oct-Dec specific) Donchian
breakout in this repo — distinct from all prior unconditional
Donchian/Turtle breakout variants (2026-09-04-054, 2026-09-07-014,
2026-09-16-174/177), which trade breakouts year-round.

## Grid test (Step 6)

`entry_window` in {15, 20, 30} x `atr_stop_mult` in {1.0, 1.5, 2.0},
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3,
2016-2026 (108 cells):

- **pass_fraction = 0.167 (18/108)**
- by_asset_class: equity 9/54, **crypto 9/54** (a rare case where crypto
  matches equity's pass rate — this seasonal window mechanic is a
  genuinely crypto-native edge, unlike most strategies tested this cron
  trigger where crypto underperforms)
- by_vol_regime: low 9/36, mid 9/36, high 0/36
- best_cell: `entry_window=15, atr_stop_mult=1.0`, BTC/USDT, high-vol,
  Sharpe 1.593
- worst_cell: same config, QQQ, high-vol, Sharpe -1.070

Local full-sample sweep across all 9 (entry_window x atr_stop_mult)
combos confirmed BTC/USDT clears Sharpe>=1.0 and MDD<=0.25 at EVERY
combination tested (Sharpe range 1.10-1.20, MDD range 0.18-0.21) — an
unusually flat, robust parameter surface. QQQ and SPY never clear
Sharpe>=1.0 at any tested combo (QQQ range -0.13 to 0.10; SPY range 0.27
to 0.49) — the calendar-window gate is simply too restrictive on equities
relative to their year-round trend character; ETH/USDT partially works
(Sharpe 0.32-0.47) but never clears the bar either.

## Single-config validation (Step 7)

Config: `entry_window=20, atr_stop_mult=1.0, trend_ma_window=50,
atr_window=14, trail_ema_window=10`, BTC/USDT, full sample 2016-2026.

| Metric | BTC/USDT |
|---|---|
| Sharpe | **1.197** (pass, ≥1.0) |
| Max Drawdown | 0.179 (pass, ≤0.25) |
| Net Sharpe after 10bps costs | 1.186 (pass, ≥0.5) |
| Walk-forward (manual 4-split) | 1.0 (pass, ≥0.75) |
| Parameter sensitivity (rel. std, 9-cell) | 0.027 (pass, ≤0.5) |
| num_trades | 19 (over 10.5 years — the seasonal gate is highly restrictive by design) |

## Decision

**ACCEPT for BTC/USDT only** (all 5 validators pass, with an
exceptionally flat/robust parameter-sensitivity surface — rel. std 0.027,
among the tightest of any strategy in this repo). **REJECT for QQQ/SPY**
(never clears Sharpe>=1.0 at any tested config — the strategy's
combination of a narrow 3-month calendar gate + trend + breakout filters
is simply too restrictive for equities' typically-smoother trend
character). ETH/USDT also rejected (positive but sub-threshold Sharpe
across the parameter surface).

## Source

https://voiceofchain.com/academy/crypto-seasonality-strategy (free,
fully disclosed rule) — read via `browser_exec`.
