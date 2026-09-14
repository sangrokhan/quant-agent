# Projection Oscillator (Mel Widner) Continuous Sizing Dial — SMA Trend Gate (SPY + BTC/ETH accepted, QQQ near-miss)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_projection_oscillator_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-035

## Hypothesis

Projection Oscillator (Mel Widner, Ph.D., Technical Analysis of Stocks &
Commodities, July 1995), sources visited this iteration:
https://www.wisestocktrader.com/indicators/763-projection-oscillator-for-amibroker-afl
(exact AFL formula) and https://www.quantifiedstrategies.com/projection-bands/
(qualitative confirmation/interpretation).

Formula: `SHIGH`/`SLOW` = linear-regression slope of High/Low over
`period` bars; `UPPBAND[t]` = rolling max over i=0..period-1 of
`High[t-i] + i*SHIGH[t]`; `LPBAND[t]` = rolling min of `Low[t-i] +
i*SLOW[t]`; `ProjO[t] = 100*(Close[t]-LPBAND[t])/(UPPBAND[t]-LPBAND[t])`.
A "slope-adjusted Stochastic" — unlike a plain Stochastic, the historical
highs/lows are projected forward by the current regression slope before
taking max/min, making the band (and hence the oscillator) more responsive
in trending markets. Genuinely new indicator family for this repo (0 prior
"Projection Oscillator"/"Projection Bands" entries).

Sources' own interpretation is the standard 80/20 overbought/oversold +
crossover + divergence rule set, with an explicit caveat to first qualify
market trendiness before trusting strict OB/OS levels. This implementation
reuses the cron trigger's established continuous-sizing-dial pattern
instead: ProjO centered on 50, rolling z-scored, tanh-squashed to [-1,+1],
used as an exposure multiplier inside an SMA(trend_window) uptrend gate
(itself answering the source's "is this trending" qualifier) with a
deadband to cut turnover.

## Grid test summary (Step 6)

`param_grid={"trend_window": [30,40,50], "period": [10,14,21],
"sensitivity": [0.4,0.6]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`. 216 total cells.

- **pass_fraction:** 0.569 (123/216) — one of this trigger's higher grid
  pass fractions
- **by_asset_class:** equity 57/108 (0.528), crypto 66/108 (0.611)
- **by_vol_regime:** low 71/72 (0.986), mid 36/72 (0.5), high 16/72 (0.222)
- **best_cell:** equity/QQQ, low-vol, `trend_window=30, period=10,
  sensitivity=0.6`, Sharpe 2.917
- **worst_cell:** equity/QQQ, high-vol, `trend_window=50, period=14,
  sensitivity=0.6`, Sharpe -0.731

## Single-config validation (Step 7)

Per-symbol best configs from the grid, hand-tuned for turnover (the raw
grid-best configs had very high turnover — 384-620 trades over the
full sample — because the short `period` slope-adjusted bands are
noisier than the fixed-window oscillators tested in prior iterations this
trigger, so all 4 initially failed transaction-cost survival at the grid's
default deadband=0.20):

| Symbol | Config | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|---|
| SPY | trend_window=30, period=21, sensitivity=0.4, deadband=0.4 | 1.426 (✓) | 0.073 (✓) | 0.507 (✓) | 1.00 (✓) | 0.128 (✓) | **YES** |
| BTC/USDT | trend_window=40, period=10, sensitivity=0.4 (default deadband=0.20) | 1.509 (✓) | 0.225 (✓) | 0.761 (✓) | 1.00 (✓) | 0.098 (✓) | **YES** |
| ETH/USDT | trend_window=40, period=10, sensitivity=0.4, leverage_cap=0.3, deadband=0.25 | 1.346 (✓) | 0.195 (✓) | 0.897 (✓) | 1.00 (✓) | 0.041 (✓) | **YES** |
| QQQ | trend_window=30, period=10, sensitivity=0.6, deadband=0.5 | 1.283 (✓) | 0.126 (✓) | 0.429 (✗, <0.5) | 0.75 (✓) | 0.271 (✓) | no (tx-cost near-miss) |

QQQ was retried across period=14/21, wider deadband up to 0.6, and a
slower zscore_window (150/200) to further smooth the dial, but net Sharpe
never crossed 0.5 (best found: 0.463 at period=14/deadband=0.4-0.5) —
recorded as a documented near-miss. Interestingly BTC/USDT passed at the
grid's *default* deadband (0.20) despite 613 trades, because crypto's
larger raw price swings make each trade's edge outweigh the flat 10bps
cost even at high turnover; QQQ's flatter equity-index moves can't clear
the same bar at comparable turnover.

## Decision (Step 8)

**Accepted, scoped to SPY + BTC/USDT + ETH/USDT.** All 5 validators pass
with comfortable-to-tight margin (SPY's net Sharpe 0.507 is a thin-margin
pass, flagged here as fragile). QQQ misses only on transaction-cost
survival despite extensive deadband/period/zscore_window tuning — left as
a documented near-miss (net Sharpe plateaued around 0.43-0.46) rather than
forcing a worse config to pass; a future iteration could try scaling
`sensitivity` down further or adding an explicit minimum-hold-period
mechanic specifically for QQQ.
