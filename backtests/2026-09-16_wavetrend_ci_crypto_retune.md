# 2026-09-16 WaveTrend Channel-Index Sizing — Crypto Retune (full universe extension)

## Hypothesis
Direct fix for prior id `2026-09-15-031` (WaveTrend Channel-Index (WT1,
LazyBear formulation) used as a continuous sizing dial inside an
SMA(trend_window) uptrend gate; accepted QQQ only, rejected SPY (Sharpe/TC
miss) and BTC/ETH (max-drawdown miss at default leverage_cap=1.0). This
sub-iteration applies this repo's standard leverage-cap-aware retune
(leverage_cap=0.25) to the identical unmodified strategy code
(`strategies/2026-09-15_wavetrend_ci_sizing_sma_trend.py`) for crypto only.
A parallel SPY fix attempt (wider trend_window/deadband sweep) was also
tried but did NOT clear the bar — kept as rejected. No new external
research; formula/source unchanged from `2026-09-15-031`
(https://pineify.app/resources/blog/wavetrend-oscillator-lazybears-momentum-indicator-guide).

## Grid test (Step 6)
`run_grid_wavetrend_ci_fixes.py`:
- **Crypto fix** (BTC/USDT, ETH/USDT), `leverage_cap in [0.25,0.3,0.4]` x
  `base_exposure in [0.1,0.15]`, `vol_regime_splits=3`: 36 cells, 28 passed,
  **pass_fraction 0.778** (low 12/12, mid 12/12, high 4/12). Best cell:
  ETH/USDT, leverage_cap=0.25/base_exposure=0.15, mid-vol Sharpe 2.250.
- **SPY fix attempt** (not adopted): `trend_window in [40,60,100]` x
  `deadband in [0.25,0.35,0.45]`, 27 cells, 9 passed, pass_fraction 0.333
  (only low-vol tercile passes; mid/high 0/9 each) — full-sample validators
  below confirm this doesn't clear the bar, SPY remains rejected.

## Single-config validation (Step 7)
Chosen crypto config: `trend_window=40, channel_length=10, average_length=21,
zscore_window=100, base_exposure=0.15, sensitivity=0.6, leverage_cap=0.25,
deadband=0.20`.

| Symbol   | Sharpe | MDD   | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel-std) |
|----------|--------|-------|-------------------------|--------------|------------------------------|
| BTC/USDT | 1.177  | 0.161 | 0.896                   | 0.75 (3/4)   | 0.049                        |
| ETH/USDT | 1.241  | 0.138 | 1.037                   | 1.00 (4/4)   | 0.047                        |

Both pass all 5 validators (note: leverage_cap=0.2 produced a degenerate
near-zero-trade `inf`-Sharpe cell and was excluded from the param-sensitivity
sweep, same pattern as the Coppock crypto retune earlier this trigger).

SPY re-check at `trend_window=100/deadband=0.25` (equity default
leverage_cap=1.0): Sharpe 0.824 (fail, threshold 1.0), TC-survival net Sharpe
0.399 (fail, threshold 0.5), MDD 0.109 (pass), walk-forward 0.75 (pass),
param-sensitivity 0.112 (pass) — **SPY stays rejected**, no fix found this
iteration.

## Decision
**Accept (crypto: BTC/USDT, ETH/USDT).** Combined with the existing
`2026-09-15-031` QQQ equity accept, WaveTrend CI's continuous-sizing dial
now covers QQQ + BTC/USDT + ETH/USDT (SPY remains excluded — decisive
Sharpe/TC-survival rejection, no rescue found).

## Source
https://pineify.app/resources/blog/wavetrend-oscillator-lazybears-momentum-indicator-guide
(unchanged from `2026-09-15-031`, no new fetch this iteration — pure own-data
parameter retune).
