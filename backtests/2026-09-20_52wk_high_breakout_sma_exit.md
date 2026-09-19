# Backtest Report: 52-Week High Breakout, 200-day SMA Exit

**Strategy file:** `strategies/2026-09-20_52wk_high_breakout_sma_exit.py`
**Date:** 2026-09-20
**Outcome:** REJECTED (near-miss on equity)

## Hypothesis

Per quantifiedstrategies.com's "52-Week High Trading Strategy"
(https://www.quantifiedstrategies.com/52-week-high-strategy/, read via
browser_exec fallback -- web_search DDGS backend hit repeated
TLS/connection-reset errors on every query this iteration), the "52-week
high effect" (academic literature, e.g. Hong/Jordan/Liu, George/Hwang)
finds stocks near their 52-week high tend to outperform going forward.
The source cites a fully-disclosed single-asset backtest (from
enlightenedstocktrading.com): buy on a new 52-week high, exit when price
crosses below its 200-day SMA ("Exit 1", the source's best-performing exit
variant: 8.6% CAGR / 44% MDD in the source's own stock-universe backtest).

Mechanical rules implemented: entry when close >= trailing 252-day rolling
max close (a genuine new high); exit when close < SMA(exit_sma_window), or
a max_hold_days=500 safety time-stop.

## Grid test summary (`grid_summary_52wk_high_breakout.json`)

- Grid: `lookback_days` in {126,189,252} x `exit_sma_window` in {100,150,200}
  = 9 combos x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 108
  cells.
- pass_fraction: 0.269 (29/108) -- moderately strong, one of the better
  grid results in this repo's recent history.
- By asset class: equity 24/54 passed, crypto 5/54 passed.
- By vol regime: low 23/36, mid 3/36, high 3/36 -- strongly low-vol-regime
  concentrated, consistent with this repo's frequent finding that
  trend/momentum strategies pass mostly in low-vol slices.
- Best cell: SPY, low-vol, lookback_days=126/exit_sma_window=100, Sharpe
  2.45 (single narrow low-vol-tercile cell).

## Full-sample parameter search (SPY + QQQ jointly, 6x7=42 combos)

Searched `lookback_days` in {63,100,126,150,189,252} x `exit_sma_window` in
{50,75,100,125,150,175,200}, optimizing for the worse of the two symbols'
full-sample Sharpe (shared-config requirement, per this repo's convention
of preferring configs that generalize across both benchmark equities).

Best shared config: `lookback_days=63, exit_sma_window=150`:

| Symbol | Sharpe | Max Drawdown |
|---|---|---|
| SPY | 0.879 | 0.162 |
| QQQ | 0.880 | 0.192 |
| BTC/USDT | 0.199 | 0.521 (fails MDD) |
| ETH/USDT | 0.221 | 0.514 (fails MDD) |

Both SPY and QQQ land just under the Sharpe >= 1.0 threshold at the best
shared config found across a 42-combo search -- a genuine near-miss
(0.88 vs 1.0 threshold), not a decisive failure. Crypto is decisively
rejected on both Sharpe and MDD.

## Decision

**REJECTED** (equity near-miss, crypto decisive reject). Sharpe on SPY/QQQ
(0.88 both) falls short of this repo's 1.0 threshold even after a 42-combo
joint parameter search; MDD passes comfortably (0.16-0.19 vs 0.25
threshold) on equity. No further validator runs (walk-forward,
transaction-cost, parameter-sensitivity) performed given the Sharpe
shortfall already disqualifies acceptance -- however this is flagged as a
worthwhile near-miss for a future loop to revisit, e.g. with:
- A volatility-regime gate (grid shows the effect is real but concentrated
  in low-vol terciles -- an explicit low-vol filter, mirroring this repo's
  BB-meanrev-QQQ-volregime construction, might push the low-vol-only Sharpe
  over threshold while accepting reduced trade frequency).
- A tighter/trailing exit instead of the flat 200d-SMA cross (the source's
  own article notes Exit 2 (25% trailing stop) and Exit 3 (100-bar lowest
  close) as alternatives not yet tried here).
- Testing on individual high-momentum stocks rather than SPY/QQQ index
  ETFs -- the source itself notes the effect is "more relevant/impressive
  for individual stocks... than for large broad indices" and its own S&P100
  cross-sectional basket backtest (feasibility-blocked here, single-symbol
  loaders/interface) reported a much stronger 16% CAGR result.
