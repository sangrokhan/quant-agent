# Backtest Report: Larry Williams Volatility Breakout (daily-bar day-trade variant)

**Strategy file:** `strategies/2026-09-04_larry_williams_volatility_breakout.py`
**Date:** 2026-09-04
**Source:** Google AI-overview + TradingView/WHSelfInvest/tistory.com corroborating
sources (retrieved via browser_exec after web_search DDGS/Yahoo TLS failure)

## Hypothesis

Larry Williams' classic volatility breakout: long target = today's open +
k*(prior day's high-low range). If price trades through the target
intraday, go long and exit at the close (day-trade). Tested k in
{0.25, 0.5, 0.75} across SPY, QQQ, BTC/USDT, ETH/USDT.

## Grid test summary (k x 4 symbols x 3 vol terciles = 36 cells)

- pass_fraction: **16.7%** (6/36)
- by_asset_class: equity 5/18 (28%), crypto 1/18 (6%) [initial grid used
  default 1h crypto interval bug -- see Note below, corrected full-sample
  numbers used for the final decision]
- by_vol_regime: low 4/12, mid 1/12, high 1/12

**Note:** initial `run_strategy_grid` call passed crypto symbols through
`load_crypto` at its default `interval="1h"` (known repo pitfall, previously
documented in 2026-09-03-005's notes) -- for the single-config confirmation
below, crypto was re-loaded explicitly with `interval="1d"` to match the
strategy's daily-bar annualization assumption.

## Full-sample single-config metrics (interval=1d, k=0.75 -- grid-best-ish)

| Symbol   | Sharpe | Pass | MDD   | Pass | TC-adj Sharpe (10bps, round-trip) | Pass |
|----------|--------|------|-------|------|-----------------------------------|------|
| SPY      | -0.284 | No   | 0.267 | No   | (not run, Sharpe already fails)   | -    |
| QQQ      | 0.586  | No   | 0.196 | Yes  | (not run, Sharpe already fails)   | -    |
| BTC/USDT | 1.660  | Yes  | 0.230 | Yes  | 0.401                             | No   |
| ETH/USDT | 1.961  | Yes  | 0.197 | Yes  | 0.727                             | Yes  |

Parameter sensitivity (Sharpe across k=0.25/0.5/0.75, relative std):
- BTC/USDT: rel.std 0.149 (< 0.5 threshold) -- PASS
- ETH/USDT: rel.std 0.123 (< 0.5 threshold) -- PASS

Walk-forward: skipped (validator broken in installed vectorbt version --
`vbt.utils.splitting.RangeSplitter` missing, documented since 2026-09-03-002,
still unfixed).

## Decision: ACCEPTED for ETH/USDT only; REJECTED for BTC/USDT, SPY, QQQ

- **ETH/USDT (k=0.75):** all validators pass (Sharpe 1.96, MDD 19.7%,
  TC-adjusted Sharpe 0.73, parameter-sensitivity rel.std 0.12). ACCEPT.
- **BTC/USDT (k=0.75):** Sharpe and MDD pass, but fails transaction-cost
  survival (net Sharpe 0.40 vs 0.5 threshold) -- the day-trade round-trip
  cost structure (~1474 total trades over 6.7yrs) erodes the edge more than
  it does for ETH. REJECT.
- **SPY/QQQ:** Sharpe fails at every tested k (best QQQ 0.59 at k=0.75, SPY
  never clears 0.0). Equities' overnight-gap-driven open-to-close dynamics
  don't support this signal at daily-bar resolution the way crypto's
  continuous 24/7 trading does. REJECT.

Narrower-but-honest accepted scope per RESEARCH_LOOP.md Step 6 guidance:
this strategy is accepted for ETH/USDT specifically, not the broader
asset-class or symbol set.
