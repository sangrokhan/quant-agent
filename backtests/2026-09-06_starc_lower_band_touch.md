# Backtest Report: STARC Bands Lower-Band-Touch Bullish Reversal (REJECTED)

**Strategy file:** `strategies/2026-09-06_starc_lower_band_touch.py`
**Date:** 2026-09-06
**Source:** https://forexbee.co/starc-bands-indicator/

## Hypothesis

Per forexbee.co's STARC Bands guide: "When [price] will reach the lower
band or (starc -) then open a buy trade by analyzing any bullish
candlestick pattern... Take profit: partially close the trade at the
middle band and then close the rest of the trade when the price touches
the other opposite band." Implemented as: entry on low touching STARC-
(SMA - multiplier*ATR) with a bullish (close>open) confirmation bar; exit
at the SMA midline or a time-stop (binary position simplification of the
source's 2-target partial-close scheme). First STARC Bands strategy in
this repo.

## Step 6 — Grid test summary (216 cells: atr_multiplier[1.5,2.0,2.5] x
sma_window[10,15,20] x max_hold_days[7,10] x 2 asset classes x 2 symbols
each x 3 vol regimes)

- **Overall pass_fraction: 0.056** (12/216) — decisively weak
- **By asset class:** equity 12/108 (0.111), crypto 0/108 (decisive reject)
- **By vol regime:** low 12/72 (0.167), mid 0/72, high 0/72 -- only works in
  a narrow low-vol slice
- **Best cell:** atr_multiplier=2.0, sma_window=10, max_hold_days=7, QQQ,
  low-vol, Sharpe=1.75

## Step 7 — Single-config validation (best cell config, QQQ, full sample
2019-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **False** | 0.194 | >= 1.0 |
| Max drawdown | True (barely) | 0.247 | <= 0.25 |
| TC survival (10bps/trade, 30 trades) | **False** | net Sharpe 0.153 | >= 0.5 |

Full-sample Sharpe collapses from the isolated low-vol grid cell's 1.75 to
0.19 -- classic narrow-slice cherry-picking. Skipped walk-forward/parameter
sensitivity given the decisive Sharpe/TC failure.

## Outcome: **REJECTED**

Decisive across the grid and full sample. Simple close>open "bullish
candle" confirmation is likely too weak a filter compared to the specific
named candlestick patterns already tested elsewhere in this repo; a future
loop could retry STARC lower-band-touch gated by an actual reversal
candlestick pattern (e.g. Hammer/Bullish Engulfing) instead of a bare
close>open bar. Keeping the file as a rejected-attempt record.
