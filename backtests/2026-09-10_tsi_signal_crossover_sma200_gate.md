# Backtest Report: TSI Signal-Line Crossover + SMA200 Uptrend Gate

**Strategy file:** `strategies/2026-09-10_tsi_signal_crossover_sma200_gate.py`
**Date:** 2026-09-10
**Outcome:** ACCEPTED (QQQ only, scoped); SPY near-miss; crypto rejected

## Hypothesis

Per Quantified Strategies' TSI explainer
(https://quantifiedstrategies.substack.com/p/true-strength-index-tsi-trading-strategy):
the True Strength Index (William Blau) is a double-smoothed momentum
oscillator (TSI = 100 * doubleEMA(price_change,25,13) /
doubleEMA(abs(price_change),25,13)) with an EMA signal line; a bullish
signal-line crossover indicates strengthening upside momentum. To avoid the
whipsaw problem of trading raw oscillator crossovers in downtrends, this
version additionally requires close > SMA(200) (uptrend gate) — a pattern
this repo has repeatedly found improves entries. First TSI strategy in this
repo (0 prior hits).

## Step 6 grid summary

Grid: `signal_window` in {7, 12} x `max_hold_days` in {20, 40} x
QQQ/SPY/BTC/ETH x low/mid/high realized-vol terciles (48 cells,
2018-01-01 to 2024-12-31). Fixed `long_window=25`, `short_window=13`,
`sma_window=200`.

- pass_fraction: 0.125 (6/48)
- by_asset_class: equity 6/24, crypto 0/24 (decisive crypto fail)
- by_vol_regime: low 6/16, mid 0/16, high 0/16 — the edge is concentrated
  entirely in low-realized-vol regimes; the strategy does not work in
  mid/high-vol conditions in this grid
- Best cell: signal_window=12, max_hold_days=40, QQQ, low-vol tercile,
  Sharpe 2.45

## Step 7 single-config validation (signal_window=12, max_hold_days=40, long_window=25, short_window=13, sma_window=200, full sample 2018-2024)

| Metric | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.007 | 0.858 | >= 1.0 | Yes / No |
| Max drawdown | 0.104 | 0.086 | <= 0.25 | Yes / Yes |
| TC survival (5bps/trade, entries+exits counted) | 0.921 | 0.705 | >= 0.5 | Yes / Yes |
| Walk-forward (4 splits) | 1.00 (4/4) | 1.00 (4/4) | >= 0.75 | Yes / Yes |
| Parameter sensitivity (relative std across signal_window x max_hold_days grid) | 0.109 | 0.201 | <= 0.5 | Yes / Yes |

Trade counts (entries only): QQQ 39, SPY 46 over ~7 years.

## Decision: ACCEPTED (QQQ only)

QQQ clears every validator (Sharpe 1.007, just above threshold; MDD, TC
survival, walk-forward, and parameter sensitivity all pass comfortably).
SPY is a near-miss on Sharpe (0.858) despite passing everything else —
scoped out of the accepted claim per this repo's convention of narrow,
honest scope rather than over-generalizing. Crypto (BTC/ETH) fails
decisively across the whole grid (0/24), and the edge only appears in
low-vol regimes — this strategy should not be trusted in mid/high
volatility conditions or on crypto.

## Source

- https://quantifiedstrategies.substack.com/p/true-strength-index-tsi-trading-strategy
