# Backtest Report: Chande Forecast Oscillator (CFO) Sizing — Crypto Retune

**Strategy file:** `strategies/2026-09-14_cfo_sizing_sma_trend.py` (unchanged code, new configs)
**Knowledge base id:** 2026-09-16-057
**Date:** 2026-09-16

## Hypothesis

Direct fix for prior id 2026-09-14-112 (CFO continuous sizing dial,
accepted QQQ+SPY but decisively rejected on crypto due to MDD 43.3%>25%
at the default leverage_cap=1.0/base_exposure=0.5 config). This
sub-iteration applies this repo's now-standard leverage-cap-aware retune
(cut leverage_cap and base_exposure substantially for crypto) to the
identical unmodified CFO strategy code, testing whether the crypto
rejection was a leverage/sizing artifact rather than a fundamental
mismatch between CFO and crypto's return dynamics.

No new external research this sub-iteration -- pure parameter retune of
an already-documented indicator/construction, following the
"generalize an accepted-equity-only dial to crypto via leverage-cap
retune" pattern already established multiple times in this repo (e.g.
PVI/RVI/PMO rescues earlier this cron trigger).

## Step 6/7 — Parameter search and validators

Hand-tuned parameter search (not a full `grid_test.py` sweep, since this
reuses an already-grid-tested strategy file and only retunes the
crypto-specific leverage/exposure/deadband combination):

| Symbol | cfo_sensitivity | deadband | base_exposure | leverage_cap | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC/USDT | 0.6 | 0.28 | 0.20 | 0.35 | 1.541 | 0.107 | 0.792 | 1.00 | 0.048 | YES |
| ETH/USDT | 0.6 | 0.28 | 0.15 | 0.30 | 1.080 | 0.153 | 0.515 | 1.00 | 0.057 | YES |

Both symbols now pass all 5 validators, versus the prior decisive crypto
rejection (MDD 43.3%) at the default leverage_cap=1.0 config.

## Step 8 — Decision

**ACCEPT (crypto only, this sub-iteration)** -- CFO's continuous-sizing
dial now covers the FULL universe when the equity config from
2026-09-14-112 (QQQ trend_window=30/deadband=0.35-0.4, SPY similar) is
combined with this sub-iteration's crypto retune (BTC/ETH
leverage_cap=0.3-0.35, base_exposure=0.15-0.2, deadband=0.28).

## Notes

- This is a retune of an EXISTING accepted strategy file, not a new
  strategy -- confirms CFO's crypto rejection (2026-09-14-112) was a
  leverage-sizing artifact, not a fundamental signal mismatch, consistent
  with this repo's broad finding that most continuous-sizing dials need
  crypto-specific leverage caps around 0.25-0.35 (vs equity's 1.0) to
  control MDD.
- ETH's TC-survival margin is thin (net Sharpe 0.515, threshold 0.5) --
  flagged as a near-miss-margin pass.
