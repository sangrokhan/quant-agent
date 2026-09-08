# Backtest report: RSI(14) oversold-exit + fixed ATR 1:2 R:R bracket (REJECTED)

**Strategy file:** `strategies/2026-09-09_rsi_oversold_atr_bracket_exit.py`

## Hypothesis

Per FxBacktest.app's original research
(https://fxbacktest.app/research/indicator-signal-win-rates/, 232,772
signals / 28 instruments / 16 years, benchmarked against a matched random
control), "RSI(14) exits oversold" was their single most statistically
significant daily-chart signal at a 1:2 risk/reward target (win rate 34.8%
vs 31.1% control, +3.7pt edge). Entry: RSI crosses back above 30 from
oversold. Exit: fixed ATR-based bracket (stop=1.5xATR(14), target=2x that
distance) or a 40-bar time cap. This repo has 30+ prior RSI-oversold
variants but none use this specific fixed R:R bracket exit mechanism
(all use oscillator/SMA-based or plain time-stop exits) -- tested here as a
genuinely distinct exit construction on QQQ/SPY/BTC/ETH daily bars.

## Step 6 grid summary (run_strategy_grid)

- param_grid: `oversold_thresh=[25,30,35]` x `rr_ratio=[1.5,2.0,3.0]`
- symbols: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- vol_regime_splits=3
- **total_cells=108, passed_cells=5, pass_fraction=0.046**
- by_asset_class: equity 5/54, crypto 0/54
- by_vol_regime: low 0/36, **mid 5/36**, high 0/36
- best_cell: oversold_thresh=30, rr_ratio=3.0, QQQ mid-vol, Sharpe=2.42
- worst_cell: oversold_thresh=30, rr_ratio=1.5, QQQ high-vol, Sharpe=-1.32

Only 5 of 108 cells passed, all clustered in the equity/mid-vol slice --
essentially no robust edge, a single narrow lucky pocket.

## Single-config validation (best grid cell: oversold_thresh=30, rr_ratio=3.0), full sample

| Symbol | Sharpe | MDD | TC-survival | Param sensitivity |
|---|---|---|---|---|
| QQQ | -0.167 (fail) | 0.337 (fail, thresh 0.25) | -0.191 (fail) | 0.826 rel-std (fail) |
| SPY | -0.046 (fail) | 0.295 (fail, thresh 0.25) | -0.068 (fail) | 1.010 rel-std (fail) |

All 4 validators fail decisively for both symbols at full sample -- the
mid-vol-tercile-only pocket that drove the grid's best cell does not
survive when the full multi-year sample (including low/high-vol periods) is
included.

## Outcome: REJECTED

Decisive rejection: 5/108 grid cells passed (4.6%), and the best config
fails all four full-sample validators on both QQQ and SPY (negative Sharpe,
MDD >30% vs 25% threshold, negative net-of-cost Sharpe, and high parameter
sensitivity rel-std >0.8). The source's own reported edge (+3.7pts win-rate
over random control at 1:2 R:R) is a small statistical edge measured across
232k signals/28 instruments/16yrs of FX/metals/indices/crypto with next-bar-
open fills -- it does not translate into a tradeable daily-bar Sharpe-based
edge on just 4 symbols here. The oscillator-entry-with-oscillator-exit
variants already tested in this repo (e.g. Connors RSI(2), R3) remain
better-performing than this fixed-bracket exit mechanism.
