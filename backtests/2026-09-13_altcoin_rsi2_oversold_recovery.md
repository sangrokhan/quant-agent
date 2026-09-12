# Altcoin RSI(2) Oversold-Recovery Mean Reversion (SOL/XRP + BTC/ETH control)

Hypothesis: CoinQuant.ai's XRP 3-approach backtest (June 2026 selloff) found
RSI(14) 30/70 mean-reversion was the only profitable approach during a
selloff, vs EMA-crossover/MACD trend-following which both lost money.
Tested whether a Connors-style RSI(2) oversold mean-reversion generalizes
better to higher-beta altcoins (SOL/USDT, XRP/USDT -- first use of either
symbol in this repo) than it has on BTC/ETH.

## Single-config results (rsi_period=2, oversold=10, exit=70, max_hold_days=10)

| Symbol | Sharpe | MDD |
|---|---|---|
| SOL/USDT | 0.029 (fail) | 0.733 (fail) |
| XRP/USDT | 0.326 (fail) | 0.618 (fail) |
| BTC/USDT | 0.036 (fail) | 0.538 (fail) |
| ETH/USDT | 0.287 (fail) | 0.594 (fail) |

## Grid summary (rsi_period x oversold x exit, 4 crypto symbols, 3 vol terciles)

pass_fraction: 0.042 (4/96)
by_symbol: SOL 1/24, XRP 0/24, BTC 3/24, ETH 0/24
by_vol_regime: low 1/32, mid 3/32, high 0/32
best_cell: BTC/USDT mid-vol, rsi_period=4/oversold=10/exit=60, Sharpe=1.555
worst_cell: BTC/USDT low-vol, Sharpe=-1.178

## Verdict: REJECTED (decisive)

Hypothesis not supported: SOL/USDT and XRP/USDT do NOT show a cleaner
mean-reversion edge than BTC/USDT -- if anything XRP was marginally the
LEAST bad (0.326 vs BTC 0.036) but still fails decisively, and SOL was
essentially the worst performer with a catastrophic 73% max drawdown.
The grid's few passing cells are concentrated on BTC (3/24) not the
altcoins the hypothesis targeted, directly contradicting the source's
narrower selloff-period observation -- CoinQuant's own result likely
reflects a very specific 3-month window (March-June 2026) rather than a
durable structural edge across this repo's longer 2020-2026 test sample.
First SOL/USDT and XRP/USDT test in this repo; both symbols confirmed
loadable via data/loaders.py's ccxt/Binance provider for future use.
