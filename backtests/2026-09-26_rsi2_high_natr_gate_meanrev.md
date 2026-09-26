# Backtest Report: RSI(2) High-NATR-Gated Mean Reversion (2026-09-26)

**Strategy file:** `strategies/2026-09-26_rsi2_high_natr_gate_meanrev.py`
**KB id:** 2026-09-26-013

## Hypothesis

Per Quantitativo's "Trading the mean reversion curve"
(https://www.quantitativo.com/p/trading-the-mean-reversion-curve, free
disclosed finding): the article's own chart ("Impact of the NATR on the
Expected Return") shows the classic RSI(2)<5 + close>SMA(200)
mean-reversion edge's expected return increases with the stock's own
Normalized ATR at entry — the OPPOSITE gate direction from this repo's
existing accepted RSI(2)+ATR% strategies (2026-09-20-140/2026-09-23-045,
both gate to LOW-vol per a different source). Tested here directly: long
when RSI(2)<entry_threshold AND close>SMA(200) AND NATR(14) is ABOVE its
own trailing 100-day median (high-vol regime); exit on RSI(2)>exit_threshold
or a 10-day time-stop.

## Grid test (Step 6)

`entry_threshold` in {5, 10, 15} x `exit_threshold` in {50, 60, 70},
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3,
2016-2026 (108 cells):

- pass_fraction = 0.167 (18/108)
- by_asset_class: equity 10/54, crypto 8/54
- by_vol_regime: low 9/36, mid 3/36, high 6/36
- best_cell: `entry_threshold=15, exit_threshold=70`, ETH/USDT, low-vol,
  Sharpe 1.659
- worst_cell: `entry_threshold=5, exit_threshold=50`, QQQ, mid-vol,
  Sharpe -0.477

A full local 9-cell (3x3) sweep of the full 2016-2026 sample, on ALL 4
symbols (36 combos total), found **no single config on any symbol clears
Sharpe>=1.0**:

| Symbol | Best full-sample Sharpe (any param combo) | Best config |
|---|---|---|
| QQQ | 0.636 | entry=15, exit=50 |
| SPY | 0.436 | entry=10, exit=50 |
| BTC/USDT | 0.759 | entry=15, exit=50 |
| ETH/USDT | 0.567 | entry=10, exit=70 |

## Decision

**REJECT (all symbols, all tested configs)**. Unlike the grid's
vol-regime-sliced cells (which surfaced apparently-attractive Sharpe
readings up to 1.66 on ETH/USDT low-vol), the full-sample Sharpe never
clears 1.0 on any symbol at any of the 9 tested (entry_threshold,
exit_threshold) combinations — this is a decisive full-sample rejection,
not a near-miss, so per RESEARCH_LOOP.md Step 7 guidance the remaining
validator suite (MDD/TC-survival/walk-forward/parameter-sensitivity) was
skipped as it cannot change the outcome. Quantitativo's own disclosed
NATR-return relationship (measured cross-sectionally across Nasdaq-100
constituents) does not transfer cleanly to single-symbol index-ETF/crypto
mean-reversion at this repo's tested parameterization — a high-vol regime
gate does not clearly outperform this repo's existing LOW-vol-gated
RSI(2) variants (2026-09-20-140/2026-09-23-045, both accepted), suggesting
the cross-sectional NATR-return finding may be driven by stock-picking
breadth (choosing the highest-NATR names among 100 constituents) rather
than a property that survives when applied to a single already-volatile
index/crypto instrument.

## Source

https://www.quantitativo.com/p/trading-the-mean-reversion-curve (free,
partially disclosed — NATR-return chart and RSI(2)/SMA(200) base rule
disclosed; full cross-sectional stock-selection/diversification mechanic
paywalled) — read via `browser_exec`.
