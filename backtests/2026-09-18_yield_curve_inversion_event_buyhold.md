# Yield Curve Inversion Event -> Fixed-N-Day Buy-and-Hold — Backtest Report

**Source:** https://www.quantifiedstrategies.com/yield-inversion-trading-strategy/
("Yield curve inversion strategy backtest no. 1", disclosed rule: "When the
yield curve gets inverted (crossing below zero), we buy S&P 500. We sell
250 trading days later.")

**Hypothesis:** Tests the source's own disclosed literal rule (debounced
inversion-event trigger, fixed hold_days window) as a standalone strategy.
Distinct from this repo's existing un-inversion-timing flat-gate
(2026-09-05-024/2026-09-10-041) and TNX-vs-own-SMA crossover (2026-09-09-051)
strategies since it's event-triggered with a FIXED holding period rather
than a continuous regime gate.

## Step 6 grid summary
`hold_days` in {125, 250, 375, 500}, symbols QQQ/SPY (equity) +
BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3, start=2000-01-01.

- pass_fraction: 7/48 = 14.6%
- by_asset_class: equity 7/24 (29.2%), crypto 0/24 (0%)
- by_vol_regime: low 6/16 (37.5%), mid 1/16 (6.3%), high 0/16 (0%)
- best_cell: hold_days=500, QQQ low-vol, Sharpe=1.58
- Best QQQ avg config: hold_days=375 (2/3 vol regimes pass)

## Step 7 single-config validators (QQQ, hold_days=375, full 2000-2026 period)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.241 | >=1.0 | **FAIL** |
| Max drawdown | 72.53% | <=25% | **FAIL** |
| Transaction cost survival | net Sharpe 0.239 | >=0.5 | **FAIL** |
| Walk-forward (manual 4-split) | 0.75 (3/4 splits positive) | >=0.75 | PASS |
| Parameter sensitivity (4-cell QQQ grid) | 0.277 | <=0.5 | PASS |

Only 5 inversion events fired over the full 26-year sample (debounced --
one hold window per distinct inversion episode), an extremely thin sample.
The full-period single-config backtest is dragged down decisively by
holding through the dot-com crash (spread inverted mid-2000, 375-day hold
window captured the NASDAQ collapse) -- confirming the source's own stated
conclusion that this is "about as good as a random 250/500-day holding
period" rather than a genuine differentiated edge: sometimes that random
window overlaps a crash.

## Decision: REJECTED (QQQ; Sharpe, max_drawdown, and transaction-cost-survival all fail decisively)

The source's own event-count (5-11 trades depending on window) is too thin
to draw a reliable edge conclusion, and this repo's longer/full-period test
confirms the strategy has no robust standalone edge -- it is essentially a
random-timing long-only bet on equities' positive drift, occasionally
captured during a crash. Not accepted per Step 8.
