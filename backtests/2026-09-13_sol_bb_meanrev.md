# SOL/XRP Bollinger Band Lower-Touch Mean Reversion

Hypothesis: CoinQuant.ai's 5-strategy Solana backtest (Nov 2025-May 2026,
SOL/USDT 4h) found Bollinger Bands(20,2) mean reversion was the only
profitable approach of 5 (+10.4% vs buy-and-hold -27.9%, Sharpe 0.65).
Tested the same mechanism on SOL/USDT and XRP/USDT (with BTC/ETH as
control) over this repo's full 2020-2026 daily-resampled crypto history,
rather than the source's narrow 6-month window.

## Grid summary (bb_window x bb_std, 4 crypto symbols, 3 vol terciles)

pass_fraction: 0.019 (2/108)
by_symbol: SOL 0/27, XRP 2/27, BTC 0/27, ETH 0/27
by_vol_regime: low 0/36, mid 2/36, high 0/36
best_cell: XRP/USDT mid-vol, bb_window=15/bb_std=2.5, Sharpe=1.691
worst_cell: BTC/USDT low-vol, Sharpe=-1.063

## Verdict: REJECTED (decisive)

SOL/USDT -- the exact symbol and mechanism the source claimed worked --
fails 0/27 over this repo's longer sample. The source's own +10.4% result
was very likely a narrow-window artifact of its specific Nov 2025-May 2026
chop/downtrend regime rather than a durable structural edge; over a
multi-year sample spanning multiple full bull/bear cycles, plain Bollinger
mean reversion does not hold up on SOL. This directly corroborates
2026-09-13-027's finding (RSI mean-reversion on the same altcoins also
failed decisively) -- across two different mean-reversion mechanisms now
tested on SOL/XRP, neither generalizes beyond a cherry-picked short window.
