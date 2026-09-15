# Backtest Report: Laguerre RSI Oversold-Recovery-to-Overbought-Exhaustion (QQQ/SPY)

## Hypothesis
Per https://www.quantifiedstrategies.com/laguerre-rsi/ (accessed via browser_exec
this iteration -- web_search's DDGS backend returned only generic results for
day-of-week/divergence angles already saturated in this repo, and web_extract's
configured backend cannot fetch page content at all): the Ehlers Laguerre RSI
is a 4-stage Laguerre-filtered RSI variant bounded in [0,1], smoother/lower-lag
than classic RSI. Disclosed rule: go long when LRSI crosses above 0.2 (oversold
recovery) and hold until LRSI crosses back below 0.8 (overbought exhaustion),
riding the full bounce-to-fade move instead of scalping the extremes.

First Laguerre RSI strategy in this repo (zero prior matches for "Laguerre" in
`strategies_index.jsonl`).

## Strategy config (best from grid)
`gamma=0.7`, `oversold_threshold=0.2`, `overbought_threshold=0.8` (default)

## Single-config validator results (QQQ, SPY; 2019-01-01 to 2026-09-01)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.250 (PASS) | 1.158 (PASS) | >= 1.0 |
| Max drawdown | 0.201 (PASS) | 0.156 (PASS) | <= 0.25 |
| Transaction cost survival (10bps/trade) | net Sharpe 1.222 (PASS) | net Sharpe 1.120 (PASS) | >= 0.5 |
| Walk-forward (4 contiguous splits, manual -- `vbt.utils.splitting.RangeSplitter` unavailable in installed vectorbt version) | 4/4 splits positive (PASS) | 4/4 splits positive (PASS) | >= 75% |
| Parameter sensitivity (gamma in {0.5,0.6,0.7,0.8}, oversold=0.2) | relative_std 0.286 (PASS) | relative_std 0.327 (PASS) | <= 0.5 |

All validators pass for both symbols -> **ACCEPT** (equity only).

## Step 6 grid summary (gamma in {0.3,0.5,0.7} x oversold_threshold in {0.15,0.2}, QQQ+SPY+BTC/USDT+ETH/USDT, vol_regime_splits=3, 2019-2026)

- total_cells=72, passed_cells=14, pass_fraction=0.194
- by_asset_class: equity 11/36 passed, crypto 3/36 passed
- by_vol_regime: low 10/24, mid 2/24, high 2/24 -- strategy is heavily low-vol-regime dependent
- best_cell: QQQ, gamma=0.7, oversold=0.15, low-vol, Sharpe=2.43
- worst_cell: ETH/USDT, gamma=0.5, oversold=0.15, high-vol, Sharpe=-0.61
- At gamma=0.7/oversold=0.2 (chosen config): QQQ passed 2/3 vol regimes (avg Sharpe 1.585), SPY passed 2/3 (avg Sharpe 1.229), BTC/USDT passed 1/3 (avg Sharpe 0.991), ETH/USDT passed 0/3 (avg Sharpe 0.819)

**Scope note**: this strategy's grid edge is concentrated in equity (QQQ/SPY)
and specifically low/mid-vol regimes at high gamma (0.7, i.e. heavier
smoothing). Crypto (BTC/ETH) did not clear the grid's per-cell Sharpe/MDD bar
consistently even at the best-performing param combo -- do not treat this as
validated for crypto.
