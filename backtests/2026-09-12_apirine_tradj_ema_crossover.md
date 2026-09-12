# Backtest Report: Apirine TRAdj EMA Dual-Length Crossover

**Strategy file:** `strategies/2026-09-12_apirine_tradj_ema_crossover.py`
**Hypothesis ID:** 2026-09-12-196
**Source:** Vitali Apirine, "True Range Adjusted Exponential Moving Average
(TRAdj EMA)", S&C January 2023 (TASC Traders' Tips 2023.01), formula from
TradingView PineCodersTASC implementation notes
(https://www.tradingview.com/script/zoO55oZJ-TASC-2023-01-TRAdj-EMA/).

## Hypothesis

TRAdj EMA modulates its EMA weighting factor by how close the current
bar's True Range is to its recent max (vs min) over a lookback window --
speeds up during volatility expansion, slows down during contraction.
Source's own suggested usage: pair two TRAdj EMAs of different lengths to
"identify turning points" -- operationalized as a fast/slow crossover.

## Grid test (Step 6): `fast_length` in {8,12} x `slow_length` in
{26,40}, QQQ/SPY equity + BTC/USDT, ETH/USDT crypto, vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.208** (10/48 cells).
- **By asset class:** equity 10/24; crypto 0/24 (decisive).
- **By vol regime:** low 8/16, mid 2/16, high 0/16.
- **Best cell:** QQQ, low-vol, `fast=8, slow=26` (Sharpe 2.34).
- Best average-Sharpe configs: QQQ `fast=8, slow=40` avg 1.113; SPY
  `fast=8, slow=40` avg 0.934 (grid-window 2019-2026).

## Single-config validation (Step 7), full 2018-2026 sample

| Symbol | Params | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param-sens rel.std | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | fast=8, slow=40 | 0.757 (**FAIL**) | 0.328 (**FAIL**) | 0.584 (pass, narrow) | 1.00 (pass) | 0.109 (pass) | 165 |
| SPY | fast=8, slow=40 | 0.677 (**FAIL**) | 0.300 (**FAIL**) | 0.456 (**FAIL**, narrow) | 1.00 (pass) | 0.193 (pass) | 162 |

Both configs fail Sharpe and MDD on the full sample despite promising
grid-window (2019-2026) averages -- the strategy generates very high
turnover (162-165 trades over ~8.5 years, roughly 19-20/year), and this
plus the 2018-2019 period (not covered by the grid) both appear to erode
the edge materially. SPY additionally fails the transaction-cost-survival
check.

## Decision: **REJECT** (both QQQ and SPY fail Sharpe/MDD on full sample;
crypto rejected decisively at grid stage)

Confirms that a pure dual-TRAdj-EMA crossover, despite the underlying
volatility-adaptive smoothing mechanism being novel, does not produce a
robust standalone signal at this turnover level. A future iteration could
revisit with a longer minimum-hold filter to reduce whipsaw trading
frequency, per this repo's established "add hysteresis" fix pattern for
high-turnover near-misses.
