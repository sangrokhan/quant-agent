# 2026-09-21 Bollinger Band SMA(200)-Gated Mean Reversion, Upper-Band Exit

**Hypothesis:** Per r/algotrading post "Surviving 2008 and 2022 with a 10%
Drawdown: A 20-Year ETF Mean Reversion Study" (u/vaanam-dev, read via
browser_exec — web_search DDGS backend TLS-erroring this iteration): entry
when close < lower Bollinger Band(20,2) AND close > SMA(200); exit when
close > UPPER Bollinger Band (not middle basis). Source's own claim: this
exit-target swap alone took SPY CAGR from 2.44% to 7.22% (MDD 12.89% to
15.24%).

**Strategy file:** `strategies/2026-09-21_bb_sma200_upperband_exit_meanrev.py`

## Step 6 grid summary (bb_window∈{15,20,25} × bb_std∈{1.5,2.0,2.5} ×
QQQ/SPY/DIA/IWM/BTC-USDT/ETH-USDT × low/mid/high vol terciles, 2019-2026)

- total_cells: 162, passed_cells: 27, pass_fraction: 0.167
- by_asset_class: equity 27/108, crypto 0/54 (decisive crypto reject)
- by_vol_regime: low 16/54, mid 10/54, high 1/54
- best_cell: QQQ low-vol tercile, bb_window=25/bb_std=2.5, Sharpe 3.080

## Full-sample sweep (2010-2026, all 9 param combos, 4 equity symbols)

Full-sample Sharpe never clears 1.0 for ANY symbol at ANY of the 9 param
combinations. Best results: QQQ 0.947 (bb_window=20/bb_std=2.5), DIA 0.940
(bb_window=20/bb_std=2.5), SPY 0.865, IWM 0.864. Max drawdown also fails
the 0.25 threshold for most combos (SPY 0.29-0.34, DIA 0.17-0.37, IWM
0.27-0.47).

## Decision: REJECT (decisive)

Despite the source's own claimed SPY improvement from the exit-target
swap, this repo's longer/different backtest window (2010-2026 vs source's
2006-2025) and different data feed do not reproduce a Sharpe >= 1.0
result for any symbol or parameter combination tested. IWM (Russell 2000
small-cap) is a particularly poor fit (MDD 0.27-0.47 across all combos).
Crypto rejected decisively (0/54 grid cells). Not revisiting this exact
construction — the source's headline numbers (CAGR/MDD/Calmar, not
Sharpe) may look more favorable on their own metric set, but this repo's
Sharpe-centric validator bar is not cleared.
