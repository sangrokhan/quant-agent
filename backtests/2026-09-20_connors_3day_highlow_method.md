# Backtest Report: Connors' 3-Day High/Low Method

**Strategy file:** `strategies/2026-09-20_connors_3day_highlow_method.py`
**Date:** 2026-09-20
**Source:** Larry Connors & Cesar Alvarez, *High Probability ETF Trading*
(2009), summarized at
https://www.quantifiedstrategies.com/larry-connors-3-day-high-low-method/
(read via browser_exec; web_search returned only generic backtesting-guide
pages, not this specific article).

## Hypothesis

Within an established long-term uptrend (close > SMA(200)), a 3-day
short-term pullback (each of 3 consecutive days shows both a lower high
AND a lower low than the prior day, while close stays below its own
5-day SMA) marks a high-probability mean-reversion long entry. Exit when
close recovers back above the 5-day SMA. This is the source's own
disclosed mechanical rule, distinct from this repo's already-tested
Lower-Highs/Lower-Lows-3-Day Reversal (2026-09-18-093/094) via the added
200-day trend filter and 5-day-SMA-based entry/exit timing (vs a plain
N-day time-stop with no trend filter).

## Grid test summary (Step 6)

Grid: `trend_window` in {150,200} x `pullback_sma_window` in {5,8} x
`confirm_days` in {2,3} x `max_hold_days` in {10,20}, symbols QQQ/SPY
(equity) and BTC/USDT, ETH/USDT (crypto), vol_regime_splits=3 (low/mid/high
realized-vol terciles), 2019-01-01 to 2026-09-01.

- **Overall pass_fraction:** 0.260 (50/192 cells, min_sharpe=1.0 per cell)
- **By asset class:** equity 34/96 (0.354) vs crypto 16/96 (0.167) --
  strategy holds up meaningfully better on equity than crypto.
- **By vol regime:** low 26/64 (0.406), mid 4/64 (0.063), high 20/64
  (0.313) -- edge concentrated in low and high vol terciles, weak in the
  middle regime.
- **Best cell:** QQQ, trend_window=200/pullback_sma_window=5/confirm_days=2/
  max_hold_days=10, low-vol regime, Sharpe 1.760.
- **Worst cell:** BTC/USDT, confirm_days=3/max_hold_days=10, mid-vol
  regime, Sharpe -0.552.

Crypto full-sample (all 4 base configs tested) never exceeded Sharpe 0.19
with very high trade counts (900-2300+ trades over the sample), indicating
the pullback pattern is far too common/noisy on 24/7 crypto bars to be a
useful timing signal there.

## Single-config validation (Step 7)

A finer full-sample sweep (`trend_window` 100-200, `pullback_sma_window`
4-7, `confirm_days` 2-3, `max_hold_days` 10-25) found the best-performing
per-symbol configs:

| Symbol | Config | Sharpe | MDD | TC-adj Sharpe | Walk-fwd | Param-sens (rel std) | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=150, pullback_sma_window=4, confirm_days=3, max_hold_days=15 | 0.963 | 0.071 | 0.819 | 1.00 (4/4) | 0.103 | 42 |
| SPY | trend_window=150, pullback_sma_window=5, confirm_days=2, max_hold_days=15 | 0.955 | 0.112 | 0.668 | 1.00 (4/4) | 0.041 | 91 |

Both symbols pass max-drawdown (<=0.25), transaction-cost survival
(net Sharpe >= 0.5 at 10bps/trade), walk-forward (4/4 splits positive
Sharpe), and parameter-sensitivity (relative std well under the 0.5
threshold -- very stable across a +/-20-day trend_window perturbation).
Both **fail** the primary Sharpe >= 1.0 threshold by a narrow margin
(0.963 and 0.955 respectively).

## Decision: REJECT (near-miss)

Sharpe ratio, the primary validator, fails on both equity symbols
(0.963 QQQ / 0.955 SPY, threshold 1.0), despite every other validator
passing cleanly and with strong stability. Crypto is decisively rejected
(grid pass_fraction 0.167, full-sample Sharpe never above 0.19). Filed as
a near-miss for a possible future rescue attempt (e.g. combining with a
vol-regime gate given the grid's low/high-vol-regime concentration, or a
finer local sweep around trend_window=150).
