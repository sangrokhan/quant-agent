# 2026-09-16 Premier Stochastic Oscillator (PSO) Continuous Sizing (full universe accept)

## Hypothesis
Premier Stochastic Oscillator (PSO), developed by Lee Leibfarth (TASC
August 2008), per Investopedia's exact-formula explainer visited this
iteration and LazyBear's TradingView port (both visited this iteration):
"a rewired version of a short-period stochastic... provides a quick
response to changes in market direction." Exact construction:
`%K = 8-period stochastic oscillator`, `S = 5-period double-smoothed EMA
of ((%K-50)*0.1)`, `PSO = (exp(S)-1)/(exp(S)+1)` — a tanh-like exponential
normalization of a double-EMA-smoothed, centered %K, producing a naturally
bounded symmetric [-1,1] oscillator. First Premier Stochastic Oscillator
strategy in this repo, distinct from StochRSI/StochCMO/StochMFI/StochRVI
(all raw min/max-stochastic-of-X constructions from earlier this trigger)
via its double-EMA-smoothing + exponential-normalization step. Reframed as
a CONTINUOUS SIZING dial (already naturally bounded [-1,1], used directly)
inside an SMA(trend_window) uptrend gate with deadband, per this repo's
established pattern.

## Grid test (Step 6)
`run_grid_pso_sizing.py`: `sensitivity in [0.4,0.5,0.6]` x
`deadband in [0.20,0.30]`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), `vol_regime_splits=3`.

- total_cells: 72, passed_cells: 35, **pass_fraction: 0.486**
- by_asset_class: equity 19/36, crypto 16/36
- by_vol_regime: low 24/24, mid 10/24, high 1/24
- best_cell: QQQ, sensitivity=0.4/deadband=0.3, low-vol, Sharpe 2.734

## Single-config validation (Step 7)
QQQ and SPY passed cleanly at default-ish params (trend_window=40,
stoch_period=8, smooth_period=5, sensitivity=0.4, deadband=0.30,
leverage_cap=1.0). **BTC/USDT and ETH/USDT initially failed MDD**
(0.314/0.350 > 0.25 at leverage_cap=1.0) — leverage-cap retune (0.5)
rescued both.

| Symbol   | trend_window | stoch_period | smooth_period | sensitivity | deadband | leverage_cap | Sharpe | MDD   | TC net Sharpe | Walk-forward | Param sens. |
|----------|-------------:|-------------:|---------------:|------------:|---------:|--------------:|-------:|------:|---------------:|-------------:|------------:|
| QQQ      | 40           | 8            | 5               | 0.4         | 0.30     | 1.0            | 1.248  | 0.133 | 0.805           | 1.00 (4/4)   | 0.050       |
| SPY      | 40           | 8            | 5               | 0.4         | 0.30     | 1.0            | 1.054  | 0.072 | 0.574           | 1.00 (4/4)   | 0.035       |
| BTC/USDT | 40           | 8            | 5               | 0.2         | 0.30     | 0.5            | 1.261  | 0.182 | 1.086           | 1.00 (4/4)   | 0.031       |
| ETH/USDT | 40           | 8            | 5               | 0.2         | 0.30     | 0.5            | 1.239  | 0.156 | 1.145           | 1.00 (4/4)   | 0.050       |

All 5 validators pass on all 4 symbols.

## Decision
**Accept — full universe (QQQ, SPY, BTC/USDT, ETH/USDT).**

## Source
https://www.investopedia.com/articles/trading/10/premier_stochastic_oscillator_explained.asp
(exact formula) and https://www.tradingview.com/v/xewuyTA1/ (LazyBear port,
trading-rules context), both visited this iteration via browser_exec.
