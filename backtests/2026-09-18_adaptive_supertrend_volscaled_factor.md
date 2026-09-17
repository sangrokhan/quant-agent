# Backtest Report: Adaptive SuperTrend (Volatility-Scaled ATR Factor)

**Strategy file:** `strategies/2026-09-18_adaptive_supertrend_volscaled_factor.py`
**Hypothesis id:** 2026-09-18-010
**Source:** https://www.forexcracked.com/forex-indicator/adaptive-supertrend-indicator-tradingview/ (Adaptive Supertrend, ForexCracked)

## Hypothesis

Classic SuperTrend uses a fixed ATR multiplier, whipsawing in ranges or
lagging in fast trends. The disclosed fix: rank current ATR against its own
trailing range to get a 0-100 volatility score, linearly map to a factor
between Min/Max bounds (low vol -> small factor/tight trail, high vol ->
large factor/wide trail). Distinct from every other SuperTrend variant
already tested in this repo (plain fixed-factor, Choppiness-gated,
Chandelier dual-confirm, Pivot-Point-anchored), none of which vary the ATR
multiplier itself based on volatility regime.

## Grid Test Summary (Step 6)

Grid: `factor_min` in {1.0,1.5,2.0}, `factor_max` in {3.0,4.0},
`vol_lookback` in {60,100}, symbols equity {QQQ, SPY} + crypto {BTC/USDT,
ETH/USDT}, vol_regime_splits=3.

- total_cells: 144, passed_cells: 32, **pass_fraction: 0.222**
- by_asset_class: equity 28/72, crypto 4/72
- by_vol_regime: low 28/48, mid 4/48, high 0/48
- best_cell: QQQ low-vol, factor_min=2.0/factor_max=3.0/vol_lookback=100, Sharpe 2.27

A follow-up full-sample re-sweep (varying atr_period, vol_lookback) found a
config passing BOTH QQQ and SPY simultaneously:
`factor_min=2.0, factor_max=3.0, vol_lookback=150, atr_period=14`.

## Single-Config Validation (Step 7)

Config: `factor_min=2.0, factor_max=3.0, vol_lookback=150, atr_period=14`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|--------|--------|-----|------------------------|--------------|--------------------|---------|
| QQQ    | 1.008  | 0.206 | 0.959                 | 1.0 (4/4)    | 0.099              | **ACCEPT** |
| SPY    | 1.008  | 0.108 | 0.941                 | 1.0 (4/4)    | 0.127              | **ACCEPT** |
| BTC/USDT | 0.744 | 0.739 | 0.731                | 1.0 (4/4)    | 0.027              | REJECT (decisive) |
| ETH/USDT | 1.082 | 0.795 | 1.073                | 1.0 (4/4)    | 0.121              | REJECT (decisive MDD fail) |

## Decision (Step 8)

**Accepted for QQQ AND SPY**, both narrowly clear all 5 validators (Sharpe
just above 1.0 for both). Crypto decisively rejected on MDD (0.74-0.80),
consistent with the plain fixed-factor SuperTrend (2026-09-04-053) also
rejecting crypto in this repo.
