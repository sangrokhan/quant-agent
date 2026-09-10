# 2026-09-11 Weekly Close-Below-Prior-Week-Low Dip-Buy (Trend-Gated)

## Hypothesis
Per SetupAlpha's "I Tested 5 'Buy The Dip' Candle Patterns on SPY" (Jul 12
2026, https://setup4alpha.substack.com/p/tested-5-buy-the-dip-patterns-spy,
visited this iteration): source discloses the exact rule and standalone
backtest for "The Weekly Close Below Low" pattern -- entry when the
current week's close < the prior completed week's low, exit on daily
close > yesterday's close. Source's own disclosed unfiltered 2000-2026 SPY
backtest: 64.13% win rate, -31.56% MDD, 4.50% CAR -- source itself calls
it "fundamentally weak" risk-adjusted. Tested here with an added
close>SMA(trend_sma_window) uptrend gate to see if it rescues the
risk-adjusted profile (successful pattern for other raw dip-buy signals
in this repo, e.g. DeMarker 2026-09-04-154).

Source: https://setup4alpha.substack.com/p/tested-5-buy-the-dip-patterns-spy (visited this iteration)

## Grid summary (run_strategy_grid, param_grid={trend_sma_window:[100,150,200], use_trend_filter:[True,False]}, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3)

- total_cells: 72, passed_cells: 7, pass_fraction: 0.097
- by_asset_class: equity 7/36, crypto 0/36 (decisive crypto rejection)
- by_vol_regime: low 1/24, mid 0/24, high 6/24 (edge concentrated almost entirely in high-vol tercile -- opposite of typical trend-filtered strategies in this repo)
- best_cell: QQQ, trend_sma_window=100, use_trend_filter=FALSE, high-vol regime, Sharpe 1.70 -- notably the trend filter is OFF in the best cell

## Single-config validation (full sample, both trend_filter on/off tested)

| Config | Symbol | Sharpe | MDD | TC-adj Sharpe (10bps, N trades) |
|---|---|---|---|---|
| trend_sma_window=200, use_trend_filter=True | QQQ | 0.645 | 0.097 | 0.080 (636 trades) |
| trend_sma_window=200, use_trend_filter=True | SPY | 0.686 | 0.097 | 0.020 (621 trades) |
| trend_sma_window=100, use_trend_filter=True | QQQ | 0.398 | 0.177 | -0.006 (550 trades) |
| use_trend_filter=False | QQQ | 0.659 | 0.393 | 0.161 (1138 trades) |
| use_trend_filter=False | SPY | 0.682 | 0.182 | 0.072 (1131 trades) |

## Decision: REJECT

Full-sample Sharpe fails the >=1.0 threshold in every configuration tested
(best 0.686 SPY with trend filter). Trade count is very high (550-1138
trades over the sample) because the "hold until close>prior close" exit
fires almost every few days, and the transaction-cost-survival check
fails decisively as a result (TC-adjusted Sharpe collapses to 0.02-0.16,
even below the already-failing gross Sharpe). The trend filter DOES
shrink MDD substantially when trend_sma_window=200 (0.097 vs 0.18-0.39
unfiltered) but does not rescue the Sharpe. Confirms the source's own
stated conclusion that this raw pattern is "fundamentally weak" even
after this repo's standard trend-filter fix attempt -- the bottleneck is
trade frequency/transaction-cost drag from the fast daily-momentum exit,
not the entry signal's directional quality. Crypto rejected decisively
(0/36) as basket-mismatch aside, same overtrading problem likely applies.
