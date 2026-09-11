# MACD-V "Rallying" Stage Momentum Breakout — Backtest Report

**Date:** 2026-09-12 | **Outcome:** REJECTED

## Hypothesis

Alex Spiroglou's MACD-V (2022, volatility-normalized MACD; NAAIM Founders
Award / CMT Charles H. Dow Award) defines seven momentum "stages". Source:
https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-v
— exact quoted rule: "Rallying. The market is rallying with strong upside
momentum when the MACD-V is between 150 and 50 (150 > X > 50) and above
its signal line."

This repo already tested the "Rebounding" stage (-150<X<50, id
2026-09-06-094, accepted for equities as a bounce-off-lows read). This
iteration tests the distinct "Rallying" stage — buying strength
confirmation (continuation) rather than buying weakness reverting — using
the identical MACD-V/Signal construction but the opposite momentum-stage
zone (50 < MACD-V < 150).

Construction: MACD-V = [(EMA12-EMA26)/ATR(26)]*100, Signal=EMA9(MACD-V).
Long entry: MACD-V crosses above Signal while 50<MACD-V<150. Exit: cross
back below Signal, MACD-V leaves the [50,150] band, or max_hold_days=30
time-stop.

## Single-config validators (QQQ / SPY, rally_low=50, rally_high=150, max_hold_days=30)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **FAIL** 0.924 | **FAIL** 0.343 |
| Max drawdown (<=0.25) | pass 0.067 | pass 0.053 |
| TC survival (net Sharpe>=0.5) | pass 0.811 | **FAIL** 0.142 |
| Walk-forward (>=0.75) | pass 0.75 | pass 0.75 |
| Parameter sensitivity (rel std<=0.5) | pass 0.176 | pass 0.483 |

QQQ is a near-miss (4/5 pass, Sharpe just short of threshold at 0.924);
SPY fails decisively on Sharpe and transaction-cost survival.

## Grid test (run_grid_macdv_rally.py)

Grid: `rally_low` in [30,50,70] x `rally_high` in [130,150,170], equity
(QQQ,SPY) + crypto (BTC/USDT,ETH/USDT), vol_regime_splits=3, 108 cells.

- pass_fraction = 0.176 (19/108)
- by_asset_class: equity 19/54 passed, crypto **0/54** (decisive reject)
- by_vol_regime: low 14/36, mid 0/36, high 5/36 — edge concentrated almost
  entirely in low-vol regime, nearly absent in mid-vol
- best_cell: rally_low=30, rally_high=130, QQQ, low-vol, Sharpe=2.24
- worst_cell: rally_low=50, rally_high=130, SPY, mid-vol, Sharpe=-0.76

## Decision: REJECT

Full-sample Sharpe fails for both QQQ and SPY at the source-disclosed
50/150 zone; SPY additionally fails net-of-cost survival. Crypto decisively
rejected (0/54). The grid's best cells cluster in low-vol equity only,
similar to most prior strategies in this repo (with 2026-09-06-094's
"Rebounding" variant being a rare exception that held across all three vol
regimes). The "Rallying" continuation read of MACD-V does not show the same
robustness as the "Rebounding" bounce-off-lows read on this asset universe.

Strategy file kept in `strategies/` as a rejected-attempt record.
