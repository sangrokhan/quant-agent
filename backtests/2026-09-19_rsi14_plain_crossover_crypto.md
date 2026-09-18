# Plain RSI(14) Standalone Crossover (CoinQuant Baseline) — Rejected (2026-09-19)

**Hypothesis:** Per CoinQuant's "ADA RSI Strategy Backtest: Does
Cardano's Volatility Make RSI Signals More Effective?"
(https://www.coinquant.ai/blog/ada-rsi-strategy-backtest-does-cardano-s-volatility-make-rsi-signals-more-effective,
found via browser_exec Google fallback after web_search DDGS backend
returned unusable results this iteration): CoinQuant's published "library
baseline" RSI mean-reversion rule -- long-only, standalone RSI(14) crosses
below 30 (entry), crosses back above 50 (exit), no trend filter -- reports
a strong Bitcoin track record (+55.69% total return over Aug 2021-Aug
2026, Sharpe 0.48, MDD 23.19%, 13 trades, 61.5% win rate). This is
genuinely distinct from every prior RSI(14)-family entry in this repo
(divergence-gated 2026-09-03-019, volume-confirmed 2026-09-05-083,
asymmetric-threshold 2026-09-11-083, dual-RSI 2026-09-09-074) -- none
tested this exact plain single-condition standard-threshold rule.

**Strategy file:** `strategies/2026-09-19_rsi14_plain_crossover_crypto.py`

## Step 6 grid summary

Grid: `rsi_entry` in {25, 30, 35} x `rsi_exit` in {45, 50, 55},
rsi_window=14, QQQ+SPY (equity) + BTC/USDT+ETH/USDT (crypto),
vol_regime_splits=3.

- total_cells: 108, passed_cells: 9, **pass_fraction: 0.083**
- by_asset_class: equity 8/54 (14.8%), crypto 1/54 (1.9%)
- by_vol_regime: low 1/36, mid 4/36, high 4/36
- best_cell: rsi_entry=30, rsi_exit=55, QQQ, mid-vol tercile, Sharpe 1.581
- worst_cell: rsi_entry=35, rsi_exit=45, BTC/USDT, low-vol tercile, Sharpe -1.096

Full raw grid: `grid_result_rsi14_plain_crypto.json`.

## Full-sample check at CoinQuant's exact published config (rsi_entry=30, rsi_exit=50, rsi_window=14)

| Symbol | Sharpe | MDD | Trades |
|---|---|---|---|
| BTC/USDT | 0.471 | 0.244 | 34 |
| ETH/USDT | 0.056 | 0.630 | 26 |
| QQQ | 0.468 | 0.224 | 20 |
| SPY | 0.207 | 0.290 | 18 |

## Decision: REJECTED (all 4 symbols, decisive)

CoinQuant's own published Bitcoin backtest (Sharpe 0.48, MDD 23.19%, 13
trades over Aug 2021-Aug 2026 on Binance spot data) did NOT independently
replicate on this repo's data (Sharpe 0.471 is directionally close, but
MDD 0.244 fails the 0.25 threshold on a razor-thin margin, and the higher
trade count here (34 vs their 13) suggests a different date range or data
source produces materially different signal frequency). ETH/USDT is a
decisive fail (Sharpe 0.056, MDD 63%). Both equity symbols also fail the
Sharpe threshold comfortably. The grid confirms this is not a data-range
artifact: pass_fraction is a weak 8.3% overall and just 1.9% on crypto
(the source's own primary domain), with the edge non-existent in the
low-vol regime and only marginally present in mid/high-vol slices. This is
an honest, valuable negative result: a widely-cited "library baseline" RSI
rule does not clear this repo's validator bar on either its native asset
(BTC) or the transfer assets tested.
