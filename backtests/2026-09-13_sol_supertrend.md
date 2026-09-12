# SOL/XRP SuperTrend Trend Following

Hypothesis: CoinQuant.ai's 3-year Supertrend backtest on SOL/USDT (2022-2026,
daily) found standard SuperTrend (ATR period=10, multiplier=3) returned
+272% (Sharpe 0.83, profit factor 1.74, max DD 46.4%) across bull/bear/chop
regimes. Tested on this repo's full 2020-2026 sample on SOL/USDT, XRP/USDT
(first SuperTrend test on either symbol) with BTC/ETH as controls.

## Single-config full-sample results (atr_period=10, multiplier=3.0)

| Symbol | Sharpe | MDD |
|---|---|---|
| SOL/USDT | 1.480 (pass) | 0.629 (fail) |
| XRP/USDT | 0.673 (fail) | 0.791 (fail) |
| BTC/USDT | 0.713 (fail) | 0.531 (fail) |
| ETH/USDT | 0.898 (fail) | 0.527 (fail) |

## Grid summary (atr_period x multiplier, 4 crypto symbols, 3 vol terciles)

pass_fraction: 0.0 (0/108) -- MDD cap of 0.25 in the grid's per-cell
validators fails universally even where per-cell Sharpe is strong
(best_cell SOL/USDT high-vol Sharpe=2.317, still fails MDD)
by_symbol: SOL 0/27, XRP 0/27, BTC 0/27, ETH 0/27

## Verdict: REJECTED (MDD decisive, Sharpe genuinely promising on SOL)

This is a notable case: SOL/USDT's full-sample Sharpe (1.480) actually
CLEARS this repo's 1.0 threshold, directly corroborating the source's own
finding that SuperTrend trend-following on SOL has genuine risk-adjusted
edge across a full multi-year cycle. However, the max drawdown (62.9%,
even worse than the source's own reported 46.4% -- likely due to this
repo's longer 2020-2026 sample capturing SOL's 2022 -90% collapse in full)
massively exceeds this repo's 25% MDD threshold. The source's own framing
("Deep drawdowns are the cost of staying in trends long enough to profit")
is honest about this tradeoff, but this repo's fixed MDD cap does not
accommodate it. Not accepted as configured; a future iteration could
explore a volatility-scaled position-sizing overlay (this repo's existing
inverse-vol-targeting construction, 2026-09-08-165) specifically to try to
shrink SOL SuperTrend's drawdown into an acceptable range while preserving
its promising Sharpe.
