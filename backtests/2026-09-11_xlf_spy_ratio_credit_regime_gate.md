# 2026-09-11 XLF/SPY (Financials-vs-Broad-Market) Credit Regime Gate

## Hypothesis
Per Google AI-overview synthesis (DiviStock Chronicles/TradingView,
visited this iteration): "The Financial Select Sector SPDR Fund (XLF) to
SPDR S&P 500 ETF Trust (SPY) relative strength ratio (XLF/SPY) serves as
a classic equity market leading indicator for credit health, systemic
risk appetite, and macroeconomic cycle inflection points... When XLF/SPY
rises, financials are outperforming... expansionary regime... When it
breaks down, it often telegraphs tightening credit conditions." First
XLF/SPY (bank/credit-sector leadership) ratio gate tested in this repo,
distinct from SOXX/QQQ, XLU/SPY, RSP/SPY, XLY/XLP, Copper/Gold.

Source: Google AI-overview synthesis of DiviStock Chronicles / TradingView / Theta Nerd (visited this iteration)

## Grid summary (run_strategy_grid, param_grid={trend_sma_window:[150,200,250], ratio_sma_window:[50,100,150]}, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3)

- total_cells: 108, passed_cells: 16, pass_fraction: 0.148
- by_asset_class: equity 16/54, crypto 0/54
- by_vol_regime: low 15/36, mid 1/36, high 0/36
- best_cell: QQQ, trend_sma_window=150, ratio_sma_window=150, low-vol regime, Sharpe 1.94

## Single-config validation (full sample)

| Config | Symbol | Sharpe | MDD | TC-adj Sharpe (10bps) | Trades |
|---|---|---|---|---|---|
| sma=150, ratio=150 | QQQ | 0.895 | 0.128 | 0.748 | 101 |
| sma=200, ratio=100 (best) | QQQ | 0.920 | 0.176 | 0.748 | 119 |
| sma=250, ratio=50 | QQQ | 0.717 | 0.212 | 0.463 | 195 |
| sma=200, ratio=100 | SPY | 0.816 | 0.179 | 0.578 | 123 |

## Decision: REJECT

Full-sample Sharpe (0.59-0.92) fails the >=1.0 threshold across every
config tested for both QQQ and SPY, though MDD passes comfortably (0.13-
0.21) and TC-survival is reasonable at moderate trade counts. This is
a near-miss family (best QQQ 0.92) rather than a decisive failure --
edge is real but insufficient on a full-sample basis, concentrated in
the low-vol tercile (15/36) with almost nothing in mid/high-vol (1/36,
0/36). Crypto rejected decisively (0/54) as expected -- no bank/credit-
sector analog for crypto assets. Worth a future revisit with a
volatility-regime co-gate (mirroring this repo's earlier successful
low-vol-percentile fixes on other near-misses) given the very strong
low-vol-tercile-only performance already visible in this grid.
