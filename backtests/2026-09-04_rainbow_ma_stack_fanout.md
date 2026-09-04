# Backtest Report: Rainbow Moving Average Stack + Fan-out Trend Following

**Strategy file:** `strategies/2026-09-04_rainbow_ma_stack_fanout.py`
**Hypothesis id:** 2026-09-04-135
**Sources:** https://www.quantifiedstrategies.com/rainbow-moving-average/ ,
https://forexmt4indicators.com/rainbow-moving-average-forex-trading-strategy/

## Hypothesis

Rainbow moving average: a cascade of `n_layers` SMAs, each an SMA of the
prior layer (progressive smoothing). Perfect bullish stacking (fastest
layer above every slower layer) plus a widening fan-out (spread between
fastest and slowest layer) signals a strong, accelerating trend, per the
sources' own trend-strength interpretation. Simplified from the sources'
full 3-indicator combo (Rainbow + HMA-dot pullback trigger + fractal
stop) to isolate the Rainbow stack/fan-out mechanic alone as an
independently testable signal (this repo already separately tested HMA
and Fractals).

## Single-config validators (QQQ, period=6, fan_threshold=0.02, max_hold_days=30 -- Step 6 grid's best low-vol cell config)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full period) | ❌ | 0.530 | ≥ 1.0 |
| max_drawdown | ✅ | 0.176 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 58 trades) | ❌ | net Sharpe 0.435 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` still broken in this install) | ✅ (borderline) | 3/4 splits positive Sharpe | ≥ 0.75 pass fraction |
| parameter_sensitivity | ✅ | relative std 0.276 (8-combo grid) | ≤ 0.5 |

## Step 6 grid summary

`param_grid={period:[4,6], fan_threshold:[0.01,0.02], max_hold_days:[30,60]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
96 cells total.

- **pass_fraction:** 0.167 (16/96)
- **by_asset_class:** equity 16/48 passed (33%); crypto 0/48 passed (0%)
- **by_vol_regime:** low 14/32; mid 2/32; high 0/32
- **best_cell:** period=6, fan_threshold=0.02, max_hold_days=30, QQQ, low-vol regime, Sharpe 1.80
- **worst_cell:** period=6, fan_threshold=0.01, max_hold_days=30, SPY, mid-vol regime, Sharpe -0.41

## Decision: REJECT

The grid's best-cell Sharpe (1.80) only holds within a narrow low-vol
tercile slice; the full-period single-config Sharpe for the same
parameters is a decisive 0.53 (well below the 1.0 threshold), and the
transaction-cost-survival check also fails at 0.435 net Sharpe. The
signal is entirely equity-only (crypto is a hard 0/48) and concentrated
almost exclusively in low-vol regimes (14/32 low vs 2/32 mid vs 0/32
high) -- the trend-strength "fan-out" mechanic seems to only add value in
already-calm trending markets, which is a narrow and not very useful
regime to condition on in practice. Not worth carrying forward without a
fundamentally different exit/filter design.
