# Coppock Curve Zero-Line-Cross Long-Only Timing — Backtest Report

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-11_coppock_curve_zero_cross.py`
**Source:** https://www.quantifiedstrategies.com/coppock-curve-strategy/

## Hypothesis

E.S.C. Coppock's 1965 momentum indicator (CoppockCurve = WMA(ROC(close,11)+ROC(close,14),10)
on monthly bars) signals a long entry when it crosses above zero and an exit when it
crosses below zero. The source's own monthly-bar S&P 500 backtest (1960-2023) found
12 trades, 100% win rate, annual return 6.11% (vs buy-hold 7.03%), but drawdown reduction
(MDD 30.16% vs buy-hold 52.56%), invested only 73.75% of the time — a drawdown-avoidance
timing overlay rather than a return booster.

Adapted here to daily bars by converting the classic 11/14/10-month windows to trading-day
equivalents (~21 trading days/month): roc1_days≈231(11mo), roc2_days≈294(14mo),
wma_days≈210(10mo), fully parametrized for the grid test.

## Grid test summary (Step 6)

`scripts/run_grid_coppock.py` — param grid `roc1_days∈{189,231,273}`,
`roc2_days∈{252,294,336}`, `wma_days∈{147,210}` × symbols `{QQQ,SPY,BTC/USDT,ETH/USDT}` ×
3 vol-regime terciles (216 total cells).

- **pass_fraction: 0.167** (36/216)
- **by_asset_class:** equity 36/108 passed, **crypto 0/108 passed** (decisive rejection on crypto)
- **by_vol_regime:** low 36/72, mid 0/72, high 0/72 (edge concentrated entirely in low-vol regime)
- **best_cell:** QQQ, roc1=231/roc2=336/wma=210, low-vol, Sharpe 2.48
- **worst_cell:** ETH/USDT, same params, low-vol, Sharpe 0.07

## Single-config validators (Step 7) — best grid config (roc1=231, roc2=336, wma=210)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward (4-split) | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | 1.016 (pass, thr 1.0) | **0.328 (FAIL, thr 0.25)** | 1.015 (pass) | 1.0 (pass) | 0.018 (pass) |
| SPY | 0.803 (FAIL, thr 1.0) | **0.341 (FAIL, thr 0.25)** | 0.802 (pass) | 1.0 (pass) | 0.037 (pass) |

Trade counts are very low (2 for QQQ, 3 for SPY over 2010-2026), consistent with the
source's own "few trades, long-term timing overlay" framing.

## Decision: REJECTED

Max drawdown fails this repo's 0.25 threshold on both QQQ (0.328) and SPY (0.341) — this
is consistent with the source article's *own* reported 30.16% max drawdown on the classic
monthly version, which also exceeds this repo's threshold even though it beats buy-and-hold's
52.56% MDD. SPY additionally fails the Sharpe threshold outright. Crypto is decisively
rejected across the whole grid (0/108). The strategy's core weakness: a pure zero-line-cross
signal with no independent stop-loss/drawdown control lets it ride out large drawdowns
(e.g. 2020, 2022) before the slow WMA-smoothed indicator flips back to flat — the smoothing
that gives it its low false-signal-rate also delays its exit during genuine crashes.

Possible future revisit: add an explicit max-drawdown/vol-regime exit gate on top of the
zero-cross signal (similar to the accepted BB-meanrev-QQQ-volregime strategy's regime-flip
exit) to cap the drawdown without abandoning the long-term momentum entry logic.
