# Perpetual Funding Rate Trend-Confirmation Gate (Crypto-only)

**Strategy file:** `strategies/2026-09-20_funding_rate_trend_confirmation.py`
**Date:** 2026-09-20
**Knowledge base id:** 2026-09-20-035

## Hypothesis

Direct economic counter-hypothesis to this cron trigger's own
2026-09-20-031 (funding-rate CONTRARIAN sizing dial, accepted). Tests
whether sustained positive funding rate can ALSO serve as a
trend-confirmation signal (genuine bullish conviction, not just crowding)
rather than only a contrarian-fade signal: long only when close >
SMA(trend_window) AND rolling-summed funding over `funding_window` days is
strictly positive. Binary AND-gate construction, distinct from the
continuous inverted sizing dial already tested.

## Grid / retune (Steps 6-7)

Initial sweep at default `leverage_cap=1.0`: strong Sharpe (BTC 1.09-1.33,
ETH 1.09-1.21) but MDD decisively fails everywhere (0.49-0.62 vs 0.25) --
same "binary gate needs a leverage-cap retune" pattern as other crypto
strategies in this repo.

| Symbol | leverage_cap | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|---|
| BTC/USDT | 0.4 | 1.334 (pass) | 0.227 (pass) | 1.111 (pass) | 1.00 (pass) | 0.146 (pass) | 149 |
| ETH/USDT | 0.3 | 1.191 (pass) | 0.199 (pass) | 1.011 (pass) | 0.75 (pass) | 0.031 (pass) | 139 |

Parameter sensitivity grid varied `trend_window` in {30,40,50} x
`funding_window` in {14,21}.

**All 5 validators pass for both symbols.**

## Decision

**ACCEPTED (crypto-only)** — BTC/USDT at trend_window=40/funding_window=14/
leverage_cap=0.4, ETH/USDT at trend_window=40/funding_window=14/leverage_cap=0.3.

## Interesting finding

Both the CONTRARIAN framing (2026-09-20-031, negative funding => bullish)
and the TREND-CONFIRMATION framing (this entry, positive funding => bullish
confirmation) pass validation on the same underlying data, at
non-overlapping trade sets (different entry logic entirely) -- suggesting
funding rate carries genuine signal in both directions depending on
construction, not just one "correct" economic interpretation. Both should
be treated as independently useful, not mutually exclusive alternatives.
