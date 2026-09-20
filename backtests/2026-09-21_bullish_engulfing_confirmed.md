# Backtest Report: Bullish Engulfing (Volume + Downtrend + Breakout Confirmed)

**Strategy file:** `strategies/2026-09-21_bullish_engulfing_confirmed.py`
**Date:** 2026-09-21

## Hypothesis

Per Google AI-overview synthesis (Dukascopy/TradingView/apptrading.ai) of
bullish-engulfing confirmation rules: prior downtrend + volume spike on the
engulfing candle + price near a local low + next-bar breakout confirmation.
First candlestick-engulfing-pattern strategy in this repo.

## Grid test summary (Step 6)

Params: trend_lookback [10,20] x vol_mult [1.2,1.5,2.0] x exit_sma_window
[20,50]; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3. 144 cells.

```
pass_fraction: 0.028 (4/144)
by_asset_class: equity 0/72, crypto 4/72
by_vol_regime: low 4/48, mid 0/48, high 0/48
best_cell: crypto BTC/USDT low-vol, Sharpe=1.31
worst_cell: equity QQQ low-vol, Sharpe=-0.90
```

Equity decisively fails across the entire grid (0/72). Crypto only passes 4
low-vol cells.

## Full-sample single-config validation (Step 7)

Broad local hand-search (trend_lookback [5,10,20] x vol_mult
[1.0,1.2,1.5,2.0] x exit_sma_window [10,20,50], 36 combos per symbol):

| Symbol | Best full-sample Sharpe | Config | Non-zero-return days |
|---|---|---|---|
| BTC/USDT | inf (degenerate) | trend_lookback=5/vol_mult=1.5/exit_sma=10 | 0 |
| ETH/USDT | 0.534 | trend_lookback=5/vol_mult=1.2/exit_sma=20 | 40 |
| QQQ | inf (degenerate) | trend_lookback=5/vol_mult=1.5/exit_sma=10 | 0 |
| SPY | inf (degenerate) | trend_lookback=5/vol_mult=1.2/exit_sma=10 | 0 |

The "best" Sharpe for BTC/USDT, QQQ, and SPY is an `inf` artifact from ZERO
trades firing at that config (the 4-condition confirmation filter --
downtrend + volume spike + near-low location + next-bar breakout -- is so
restrictive that no bars satisfy it over the full 2018-2026 sample for those
symbols/configs). ETH/USDT is the only symbol with a genuine trade count
(40 non-zero-return days), and its best full-sample Sharpe (0.534) still
falls well short of the 1.0 threshold.

## Decision (Step 8)

**REJECT** -- decisive. The 4-condition confirmation stack (downtrend +
volume + location + breakout-confirmation) over-restricts the signal to
near-zero trade counts on 3/4 symbols, and the one symbol with a tradable
sample size (ETH/USDT) still fails Sharpe by a wide margin. The combined
filter is too conservative to produce a viable single-symbol time-series
strategy from what the sources describe as an inherently weak standalone
two-candle pattern.
