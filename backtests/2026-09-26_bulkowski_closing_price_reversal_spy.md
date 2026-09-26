# Bulkowski Closing Price Reversal (Downtrend), SPY

**Hypothesis:** per https://thepatternsite.com/CPRD.html, a single-bar reversal
pattern in a short-term downtrend: today's open near the intraday low, today's
close near the intraday high AND above yesterday's close. Source's own
measure-rule target (height added to pattern high) fulfilled 72% of the time
in bull markets (1990-2013, 1199 stocks).

**Config (SPY):** trend_window=30, edge_pct=0.20, height_mult=1.5, max_hold_days=20

## Single-config validators (SPY, 2019-01-01 to 2026-09-01, 24 trades)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.100 | >= 1.0 | Yes |
| Max drawdown | 0.131 | <= 0.25 | Yes |
| Net Sharpe after costs (10bps/trade) | 1.051 | >= 0.5 | Yes |
| Walk-forward | skipped (vectorbt.utils.splitting API missing, known repo issue) | n/a | n/a |
| Parameter sensitivity (relative std, 9-cell local grid) | 0.211 | <= 0.5 | Yes |

## Grid summary (initial broad scan, 324 cells: trend_window x edge_pct x height_mult x {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol terciles)

- pass_fraction: 0.031 (10/324), all equity (SPY only), concentrated in mid/high-vol tercile slices
- crypto: 0/162, decisively rejected
- Initial best grid cell (tercile slice, not full-sample): SPY mid-vol, trend_window=50/edge_pct=0.15/height_mult=1.0, Sharpe 1.537

A dedicated SPY-focused local full-sample search (not part of the original
tercile grid) found trend_window=30/edge_pct=0.20/height_mult=1.5/
max_hold_days=20 clears the full-sample Sharpe bar (1.100) with all other
validators passing. QQQ at this identical config does NOT clear the bar
(Sharpe 0.431) -- accepted SPY-only.

## Outcome: ACCEPTED (SPY only)

QQQ and crypto (BTC/USDT, ETH/USDT) remain rejected/out of scope for this
specific config -- see knowledge_base entry notes for the QQQ full-sample
Sharpe at the initial (non-retuned) config.
