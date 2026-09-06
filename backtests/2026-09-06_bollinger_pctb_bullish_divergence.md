# Backtest Report: Bollinger %B bullish divergence

**Strategy file:** `strategies/2026-09-06_bollinger_pctb_bullish_divergence.py`
**Date:** 2026-09-06
**Symbols tested:** QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
**Timeframe:** 1d

## Hypothesis

Per a Google AI-overview synthesis of Ultra Blue Forex / The Trading Pit
%B-divergence explainers (searched this iteration), a bullish %B
divergence (price makes a lower low while %B makes a higher low, i.e.
selling pressure exhausting despite the new price low) followed by %B
crossing back upward is a long entry signal. First %B-DIVERGENCE strategy
in this repo -- distinct from every plain %B threshold/mean-reversion
variant already tested (2026-09-04-107, 2026-09-05-011, 2026-09-06-092,
2026-09-06-119), none of which compare price's swing structure against
%B's swing structure.

## Step 6 grid summary (QQQ/SPY/BTC-USDT/ETH-USDT, swing_lookback in
[10, 20] x confirm_level in [0.15, 0.2, 0.3] x max_hold_days in
[10, 15, 20], vol_regime_splits=3)

```
total_cells: 216
passed_cells: 7
pass_fraction: 0.0324
by_asset_class: equity 7/108, crypto 0/108
by_vol_regime: low 0/72, mid 6/72, high 1/72
best_cell: swing_lookback=20, confirm_level=0.2, max_hold_days=10, QQQ, mid-vol, sharpe=1.251
worst_cell: swing_lookback=10, confirm_level=0.15, max_hold_days=10, SPY, low-vol, sharpe=-0.917
```

## Single-config validation (best grid config: swing_lookback=20,
confirm_level=0.2, max_hold_days=10; QQQ full sample 2019-01-01 to
2026-09-01, 39 trades)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.462 | >= 1.0 |
| Max drawdown | PASS | 0.179 | <= 0.25 |
| Transaction cost survival (10bps/trade) | **FAIL** | 0.392 net Sharpe | >= 0.5 |
| Walk-forward (4 contiguous splits) | PASS | 0.75 (3/4 splits positive) | >= 0.75 |
| Parameter sensitivity (18-cell QQQ sweep) | **FAIL** | relative_std 12.284 | <= 0.5 |

Three of five validators fail, including an extreme parameter-sensitivity
failure (relative_std 12.28 -- among the highest seen in this repo's
history), indicating the divergence detection logic is highly sensitive to
the exact swing-lookback/confirm-level choice rather than capturing a
robust repeatable pattern.

## Decision: REJECTED

Decisive failure on Sharpe, transaction-cost survival, and (severely)
parameter sensitivity. Max drawdown and walk-forward pass, but the extreme
parameter instability means the grid's apparent best_cell (Sharpe 1.25) is
not a reliable representation of the strategy's edge -- this looks like
noise-fitting rather than a genuine divergence signal.
