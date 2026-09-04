# Backtest Report: Dual Momentum (Gary Antonacci / GEM-style) Rotation

**Strategy file:** `strategies/2026-09-04_dual_momentum_rotation.py`
**Date:** 2026-09-04
**Source:** https://www.quantifiedstrategies.com/dual-momentum-trading-strategy/
(retrieved via browser_exec after web_search DDGS/Yahoo TLS failure)

## Hypothesis

Monthly-rebalanced dual momentum: hold whichever of two candidate assets
(primary vs companion) has the higher trailing 12-month return, but only if
that asset's own trailing return is positive (absolute momentum gate);
otherwise go to cash. Tested QQQ/SPY (equity pair) and BTC/USDT/ETH/USDT
(crypto pair) as the two rotation universes, using cash as the safe-haven
proxy (no bond ETF data available via this repo's loaders).

## Full-sample metrics (lookback_days=252)

| Pair          | Sharpe | Pass | MDD   | Pass |
|---------------|--------|------|-------|------|
| QQQ/SPY       | 1.086  | Yes  | 0.286 | No   |
| BTC/USDT-ETH  | 1.051  | Yes  | 0.572 | No   |

## Lookback sensitivity (QQQ/SPY pair, 126/189/252-day lookback)

| Lookback | Sharpe | Pass | MDD   | Pass |
|----------|--------|------|-------|------|
| 126d     | 0.972  | No   | 0.286 | No   |
| 189d     | 0.997  | No   | 0.286 | No   |
| 252d     | 1.086  | Yes  | 0.286 | No   |

MDD is **identical (28.6%)** across all three lookbacks for QQQ/SPY --
strongly suggests the drawdown is driven by a specific historical episode
(most likely the 2022 rate-hike drawdown, which co-occurred across QQQ and
SPY simultaneously, making the relative-momentum signal ineffective at
avoiding it since both candidates fell together) rather than being
sensitive to the momentum-lookback parameter itself.

## Decision: REJECTED

Sharpe passes at the 252-day (canonical GEM) lookback for both pairs, but
MDD fails at every tested configuration -- QQQ/SPY at 28.6% (just above the
25% budget, a genuine near-miss) and BTC/ETH decisively at 57.2%. The
cash-as-safe-haven substitution (used because this repo's loaders don't
expose a bond ETF) is the most likely structural weakness: Antonacci's
original GEM uses AGG (Treasury bonds) as the flight-to-safety asset during
drawdowns, which itself has positive expected return and low correlation to
equities -- sitting in 0%-return cash instead removes that diversification
benefit and lets the strategy's cash periods drag on relative performance
without cushioning the drawdown the way a bond position would.

Future idea: if an equity-ETF ledger like a Treasury-bond ETF becomes
available via data/loaders.py, retest with a genuine 3-way GEM
(equity/international-equity/bond) rather than the simplified two-way +
cash proxy tested here -- the QQQ/SPY MDD (28.6%) is close enough to the
25% budget that a real bond safe-haven could plausibly close the gap.
