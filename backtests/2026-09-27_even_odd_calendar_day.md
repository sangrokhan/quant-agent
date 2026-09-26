# Backtest Report: Even-vs-Odd Calendar-Day Trading Strategy

**Strategy file:** `strategies/2026-09-27_even_odd_calendar_day.py`
**Date:** 2026-09-27
**Source:** https://www.quantifiedstrategies.com/even-vs-odd-days-trading-strategy/
(Oddmund Groette, read via browser_exec).

## Hypothesis

S&P 500 close-to-close gains concentrate disproportionately on EVEN
calendar days of the month vs ODD days, per the source's own 1993-present
backtest. Source itself is explicit this is "most likely...the result of
chance" -- tested here anyway as a fully disclosed, falsifiable numeric
rule (not invented from model recall).

## Grid test summary (Step 6)

Grid: `target_parity in [even, odd]` x equity {QQQ, SPY} + crypto
{BTC/USDT, ETH/USDT} x 3 vol-regime terciles, 2019-2026.

- **Overall pass_fraction: 0.25 (6/24 cells)**
- **by_asset_class:** equity 5/12 (0.417); crypto 1/12 (0.083)
- **by_vol_regime:** low 5/8; mid 1/8; high 0/8
- **best_cell:** SPY low-vol, `target_parity=even`, Sharpe 2.24

## Standard validators (Step 7) — best config: `target_parity=even`

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.920 — **FAIL** | 0.893 — **FAIL** |
| Max Drawdown (<=0.25) | 0.292 — **FAIL** | 0.273 — **FAIL** |
| TC survival (5bps/trade, min net Sharpe 0.5) | 0.338 — **FAIL** | 0.225 — **FAIL** |

## Decision: **REJECTED (decisive, triple failure)**

Fails all three validators run on both symbols. The construction is
active on ~950 of the sample's ~1930 trading days (roughly half, as
expected for a parity split), so it behaves almost like a diluted
buy-and-hold with no real edge and full market-drawdown exposure (MDD
0.27-0.29, essentially matching unconditional QQQ/SPY drawdowns over this
period) -- confirming the source's own honest caveat that the effect is
"most likely...the result of chance" and not a tradeable edge. Not worth
pursuing further; logged as a straightforward, expected rejection.
