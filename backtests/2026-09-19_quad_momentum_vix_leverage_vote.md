# 4-Factor VIX/SPX/VWO/BND Momentum Leverage Vote — QQQ Accepted (2026-09-19)

**Hypothesis:** Per Cesar Alvarez's "UPRO/TQQQ Leveraged ETF Strategy"
(https://alvarezquanttrading.com/blog/upro-tqqq-leveraged-etf-strategy/,
read via browser_exec after web_search DDGS backend returned unusable
results this iteration): a monthly-rebalanced 4-factor risk-on vote (VIX
<= threshold, SPX > SMA200, VWO 1-3-6-12-week blended momentum positive,
BND 1-3-6-12-week blended momentum positive) gates leverage tier: 4/4
votes = 2x leveraged long (source: UPRO+TQQQ); 2-3/4 votes = 1x unleveraged
long (source: QQQ+SPY); 0-1/4 votes = TLT defensive leg (gated by TLT's
own SMA200 trend, else cash). Adapted to this repo's single-symbol
interface as a variable exposure multiplier on the primary asset's own
return, substituting TLT's own return series for the bond leg (same
substitution pattern as the already-tested 2026-09-18-104 SPY/SSO/TLT
2-factor variant). This 4-factor version adds two independent
cross-asset momentum votes (VWO, BND) not present in that 2-factor
predecessor.

**Strategy file:** `strategies/2026-09-19_quad_momentum_vix_leverage_vote.py`

## Parameter sweep (QQQ, full sample)

| leverage_multiplier | vix_threshold | Sharpe | MDD |
|---|---|---|---|
| 1.0 | 20 | 1.197 | 0.203 |
| **1.0** | **25** | **1.352** | **0.203** |
| 1.25 | 20 | 1.173 | 0.215 |
| 1.25 | 25 | 1.339 | 0.215 |
| 1.5 | 20 | 1.142 | 0.238 |
| 1.5 | 25 | 1.317 | 0.238 |

SPY never clears the Sharpe threshold at any tested combination (best
0.592 at lev=1.5/vt=25) — the source's own strategy is built around
QQQ-family leveraged ETFs (TQQQ), so this is unsurprising and QQQ is the
natural primary asset here.

Note: `leverage_multiplier=1.0` at the accepted config means the "4/4
votes" leg applies NO extra leverage over the "2-3/4 votes" leg — both
resolve to the same 1.0x primary-asset exposure. Testing showed any
leverage_multiplier > 1.0 (approximating the source's literal UPRO/TQQQ 2x
overlay) pushes MDD above the 0.25 cap while only modestly improving
Sharpe. The accepted config is therefore closer in spirit to "stay
invested unless 3+ of 4 risk indicators turn negative, then rotate to
TLT" than to the source's literal 2x-leverage-tier construction — an
honest scope narrowing rather than a literal implementation of the
source's leverage tiers.

## Step 7 validation (QQQ, leverage_multiplier=1.0, vix_threshold=25.0)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.352 | >= 1.0 | PASS |
| Max drawdown | 0.203 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 29 trades) | net Sharpe 1.314 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 3/4 positive = 0.75 | >= 0.75 | PASS |
| Parameter sensitivity (vix_threshold x leverage_multiplier, 9 cells) | CV=0.091 | <= 0.5 | PASS |

Full raw validators: `validators_quad_momentum_vix.json`.

## Decision: ACCEPTED (QQQ only, leverage_multiplier=1.0, vix_threshold=25.0); REJECTED (SPY, decisive Sharpe fail across all tested configs)

Crypto not tested (this strategy structurally requires ^VIX/VWO/BND/TLT
equity-market cross-asset data with no crypto analogue; feasibility-scoped
to equity only, same class of narrowing as other VIX/cross-asset-gated
strategies in this repo).
