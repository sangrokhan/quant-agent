# Connors RSI (CRSI) Composite Mean-Reversion — Backtest Report (2026-09-04)

## Hypothesis
Larry Connors' composite RSI (CRSI) averages three sub-indicators for a
faster, more responsive short-term oscillator than the classic 14-day RSI:
1. RSI(3) of closing price (standard Wilder RSI, short lookback).
2. RSI(2) of the up/down streak length (consecutive up/down close count).
3. 100-day PercentRank of today's 1-day rate-of-change.
CRSI = mean of the three, textbook CRSI(3,2,100). Because CRSI moves much
faster than a 14-day RSI, overbought/oversold bands sit far wider (~90/10)
than classic 70/30. Long-only entry when CRSI closes below entry_threshold,
exit when CRSI closes back above exit_threshold, or after max_hold_days
time-stop.

Source: https://www.quantifiedstrategies.com/connors-rsi/ — source's own SPY
backtest: "buy CRSI<15, sell CRSI>85" gave best profit factor (~2.08/288
trades).

## Grid summary (Step 6)
`param_grid={entry_threshold:[10,15,20], exit_threshold:[70,85]}`
(rsi_period=3, streak_period=2, pctrank_period=100, max_hold_days=10 held
fixed), symbols `{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01..2026-09-01.

- total_cells=72, passed_cells=15, **pass_fraction=0.208**
- by_asset_class: equity 15/36, crypto **0/36**
- by_vol_regime: low 10/24, mid 1/24, high 4/24
- best_cell: entry_threshold=15, exit_threshold=70, QQQ, low-vol, Sharpe=3.04
- worst_cell: entry_threshold=10, exit_threshold=70, QQQ, mid-vol, Sharpe=-1.18

Unlike most prior trend-following strategies in this repo (which
concentrate passes in low-vol only), this mean-reversion strategy also
picks up 4/24 high-vol passes — consistent with mean-reversion working
better than trend-following in choppier regimes, though the effect is
modest.

## Single-config validation (Step 7)
Config: rsi_period=3, streak_period=2, pctrank_period=100,
entry_threshold=15.0 (source's own best-profit-factor entry level),
exit_threshold=70.0 (best grid cell; tighter than source's 85), max_hold_days=10.
Full sample 2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **1.096 (pass)** | 0.912 (fail) |
| Max drawdown (<=0.25) | 0.107 (pass) | 0.081 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 0.958 (pass) | 0.742 (pass) |
| Walk-forward, 4 splits (>=0.75 pass frac) | 0.75 (pass; 1/4 splits negative) | 1.0 (pass) |
| Parameter sensitivity (entry_threshold in {10,15,20}, rel std <=0.5) | 0.387 (pass) | 0.242 (pass) |
| num_trades | 72 | 70 |

## Decision (Step 8)
**Accept for QQQ** (entry_threshold=15, exit_threshold=70, max_hold_days=10)
— all 5 validators pass (walk-forward is a borderline pass at exactly the
0.75 threshold — 1 of 4 quarters was negative — worth flagging for a future
tighter-parameter revisit).
**Reject for SPY** — Sharpe (0.912) narrowly misses the 1.0 threshold;
all other validators pass, so this is a near-miss.
**Reject for crypto (BTC/USDT, ETH/USDT)** — 0/36 grid cells pass; a
mean-reversion oscillator tuned on daily-close equity streak/ROC patterns
does not transfer to crypto's different volatility/return structure.
