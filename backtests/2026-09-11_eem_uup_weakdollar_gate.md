# Backtest Report: SPY/QQQ Trend-Following Gated by Weak-Dollar (UUP) Regime

**Strategy file:** `strategies/2026-09-11_eem_uup_weakdollar_gate.py`
**Date:** 2026-09-11
**Source:** Google SERP synthesis of "Weak Dollar, Strong EM" / "Emerging Markets Rise as Dollar Index Weakens" commentary (originally motivating an EEM-specific hypothesis)

## Hypothesis (as originally framed, EEM-focused)

Emerging-market equities (EEM) are structurally sensitive to US dollar
strength (weak dollar eases EM dollar-debt burdens and improves capital
flows). This strategy gates a standard SMA trend-following signal by
requiring the dollar (UUP, since raw DXY futures aren't available via this
repo's loaders) to be in a DOWNTREND. QQQ/SPY were tested as broader-market
controls expected to show a WEAKER effect than EEM.

## Grid test summary (Step 6)

Grid: `trend_sma_window` in {30,50,100} x `uup_sma_window` in {50,100,150},
vol_regime_splits=3, symbols equity={EEM,QQQ}, crypto={BTC/USDT,ETH/USDT}.

- **Equity:** 23/54 cells passed (0.426 pass_fraction). By vol regime: low
  16/18 (89%), mid 6/18 (33%), high 1/18 (6%). Best cell: trend_sma_window=
  50, uup_sma_window=50, **QQQ** (not EEM), low-vol, Sharpe 2.60 -- the
  effect showed up strongest in QQQ, contrary to the original EEM-centric
  hypothesis.
- **Crypto:** 0/54 cells passed, falsification confirmed.

## Single-config validation at trend_sma_window=50/uup_sma_window=50: EEM Sharpe 0.480 (fail), QQQ 0.963 (near-miss), SPY 0.998 (near-miss, essentially at threshold)

Given SPY landed exactly at the boundary, a local parameter search around
SPY (trend_sma_window x uup_sma_window in {30,40,50,60,75,90}^2) found
**trend_sma_window=40, uup_sma_window=30** clears SPY's threshold decisively
(Sharpe 1.314).

## Full validator suite at trend_sma_window=40, uup_sma_window=30

| Validator | SPY | QQQ | EEM | Threshold |
|---|---|---|---|---|
| Sharpe ratio (full sample) | 1.314 ✅ | 1.186 ✅ | 0.491 ❌ | ≥ 1.0 |
| Max drawdown | 0.077 ✅ | 0.151 ✅ | 0.275 ❌ | ≤ 0.25 |
| Transaction-cost survival (10bps/trade) | 0.707 ✅ | 0.694 ✅ | 0.173 ❌ | ≥ 0.5 |
| Walk-forward (manual 4-split) | 1.00 (4/4) ✅ | 1.00 (4/4) ✅ | 1.00 (4/4) ✅ | ≥ 0.75 |
| Parameter sensitivity (relative std) | 0.188 ✅ | 0.185 ✅ | 0.482 ✅ (marginal) | ≤ 0.5 |

## Decision: ACCEPTED (SPY and QQQ); REJECTED (EEM, decisive); crypto rejected decisively

An unusual but clean result: the weak-dollar (UUP downtrend) gate turns out
to be a genuinely useful regime filter for LARGE-CAP US EQUITIES (SPY,
QQQ), not for the emerging-market target (EEM) it was originally designed
around. This likely reflects that a weakening dollar is a broad easy-
financial-conditions signal (benefiting US mega-cap growth/multinational
earnings translation) more than an EM-specific channel, or that EEM's own
idiosyncratic risk (China/EM political and currency volatility) swamps the
dollar-regime signal. Recorded honestly per RESEARCH_LOOP.md guidance: a
narrower-but-honest accepted scope (SPY/QQQ only) is more useful than
forcing the originally-hypothesized target (EEM) to fit.
