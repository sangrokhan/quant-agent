# Backtest Report: Time Segmented Volume (TSV) zero-line + signal-MA crossover

**Strategy file:** `strategies/2026-09-06_tsv_signal_ma_crossover.py`
**Date:** 2026-09-06
**Symbols tested:** QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
**Timeframe:** 1d

## Hypothesis

Per QuantifiedStrategies.com's TSV article (source:
https://www.quantifiedstrategies.com/time-segmented-volume/, newly visited
this iteration), the Time Segmented Volume indicator (Worden Brothers)
sums (close change * volume) over a rolling window to gauge accumulation
vs. distribution, with the article's own chart caption showing a
"13-period moving average smoothing line" applied to the raw TSV as an
"objective signal filter." The exact numeric backtest rule is paywalled,
so this repo also drew on a Google AI-overview synthesis of TradingView/
Investopedia TSV rules (moving-average-confirmation entry: TSV crossing
above its own signal MA, especially transitioning from negative to
positive) to build one concrete rule: long entry when TSV crosses above
its signal-line SMA while TSV >= 0; exit on the reverse crossover, TSV
falling below zero, or a time-stop. First Time-Segmented-Volume-family
strategy in this repo -- distinct from every OBV/AD-Line/MFI/Chaikin
volume indicator already tested (TSV weights volume by raw price CHANGE
over the segment window, not dollar-flow or directional sign).

## Step 6 grid summary (QQQ/SPY/BTC-USDT/ETH-USDT, tsv_window in
[13, 26] x signal_window in [13, 20] x max_hold_days in [15, 20, 30],
vol_regime_splits=3)

```
total_cells: 144
passed_cells: 9
pass_fraction: 0.0625
by_asset_class: equity 9/72, crypto 0/72
by_vol_regime: low 6/48, mid 3/48, high 0/48
best_cell: tsv_window=13, signal_window=20, max_hold_days=20, QQQ, low-vol, sharpe=1.409
worst_cell: tsv_window=26, signal_window=13, max_hold_days=15, QQQ, high-vol, sharpe=-1.674
```

Low pass fraction, equity-only, low-vol concentrated, crypto categorically
0/72 -- signal generalizes poorly across regimes/asset classes.

## Single-config validation (best grid config: tsv_window=13,
signal_window=20, max_hold_days=20; QQQ full sample 2019-01-01 to
2026-09-01, 69 trades)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.556 | >= 1.0 |
| Max drawdown | PASS | 0.178 | <= 0.25 |
| Transaction cost survival (10bps/trade) | **FAIL** | 0.392 net Sharpe | >= 0.5 |
| Walk-forward (4 contiguous splits) | PASS | 4/4 splits positive Sharpe | >= 0.75 |
| Parameter sensitivity (12-cell QQQ sweep) | **FAIL** | relative_std 1.744 | <= 0.5 |

Three of five validators fail decisively (Sharpe well below threshold,
fails after transaction costs, and highly sensitive to parameter choice --
relative_std 1.74 means Sharpe swings from strongly negative to strongly
positive across the grid, i.e. no robust edge). This is a clean reject, not
a near-miss.

## Decision: REJECTED

Decisive failure on Sharpe, transaction-cost survival, and parameter
sensitivity. The "best cell" Sharpe of 1.41 in the grid appears to be a
lucky low-vol-regime slice rather than a genuine full-sample edge -- the
full-period QQQ Sharpe (0.556) and the high parameter sensitivity confirm
this is not a robust strategy as currently specified.
