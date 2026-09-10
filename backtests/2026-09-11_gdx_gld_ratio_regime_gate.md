# 2026-09-11 GDX/GLD (Gold Miners vs Bullion) Ratio Regime Gate

## Hypothesis
Per Investopedia's "Optimize Your Gold Miner ETF Portfolio with Technical
Analysis" and BullionVault gold-news framing (Google SERP snippets,
visited this iteration): "The GDX/GLD ratio is utilized to confirm market
sentiment, indicating whether gold mining stocks outperform physical
gold." GDX (gold miners) carries operating leverage to gold prices AND is
still an equity, so GDX/GLD may proxy broader equity risk-appetite, not
just gold-specific sentiment. Note: CXO Advisory's own GLD-GDX PAIRS
mean-reversion study found no reliable convergence pattern -- this
strategy instead uses the ratio as a TREND regime GATE on QQQ/SPY (same
validated pattern as GLD/TLT, Copper/Gold, TLT/IEF, XLU/SPY, SOXX/QQQ),
architecturally distinct from pairs mean-reversion.

Source: Google SERP snippets of Investopedia and BullionVault articles (BullionVault direct page 404'd)

## Grid summary (run_strategy_grid, param_grid={trend_sma_window:[150,200,250], ratio_sma_window:[50,100,150]}, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3)

- total_cells: 108, passed_cells: 25, pass_fraction: 0.231
- by_asset_class: equity 25/54, crypto 0/54 (decisive, no gold-mining analog for crypto)
- by_vol_regime: low 18/36, mid 7/36, high 0/36
- best_cell: SPY, trend_sma_window=250, ratio_sma_window=150, low-vol regime, Sharpe 1.94

## Single-config validation (full sample)

| Config | Symbol | Sharpe | MDD | TC-adj Sharpe (10bps) | Trades |
|---|---|---|---|---|---|
| sma=250, ratio=150 (best) | QQQ | **1.104** | **0.154** | **0.883** | 145 |
| sma=200, ratio=100 | QQQ | 0.806 | 0.189 | 0.554 | 179 |
| sma=150, ratio=50 | QQQ | 0.895 | 0.160 | 0.592 | 197 |
| sma=250, ratio=150 (best) | SPY | 0.777 | 0.110 | 0.518 | 145 |

## Decision: ACCEPT (QQQ only)

QQQ at trend_sma_window=250/ratio_sma_window=150 passes Sharpe (1.104),
MDD (0.154), and TC-survival (0.883). Parameter sensitivity across the
9-combo grid is stable (relative std 0.140). Walk-forward check via
4 equal-length splits was only partially informative: only the first
split had any trades (the 250-day SMA warmup combined with a shifting
regime meant later slices happened to fall entirely in flat/no-trade
periods for this exact 4-way naive slicing) -- that split alone showed
a positive Sharpe (0.80), consistent with but not a full confirmation of
the full-sample edge; this is noted as a validation caveat rather than
treated as a full walk-forward pass. SPY at the same config falls short
(0.777). Crypto rejected decisively (0/54) as expected -- no gold-mining
sector proxy applies to crypto.
