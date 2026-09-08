# Choppiness Index Falling-Edge + EMA Trend + Donchian Breakout — Backtest Report

**Date:** 2026-09-08 | **Strategy file:** `strategies/2026-09-08_chop_falling_edge_breakout.py` | **Outcome: REJECTED**

## Hypothesis
Per trendsandbreakouts.com's Choppiness Index trading-rules explainer
(bing.com browser fallback — web_search DuckDuckGo backend errored on the
first query), the source's explicit workflow is: take long breakouts only
when price is above a rising EMA, CI is FALLING from a higher zone (regime
transitioning out of chop, not a static low reading), and price breaks a
well-defined resistance level. Distinct from the already-tested
2026-09-04-059 (static CI<38 threshold, no falling-edge/breakout trigger).

Source: https://trendsandbreakouts.com/choppiness-index

## Grid test (chop_high_zone=[55,61.8,70] x donchian_window=[15,20,30], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 108 cells total, 17 passed (pass_fraction 0.157)
- By asset class: equity 17/54, crypto 0/54 (decisive fail)
- By vol regime: low 11/36, mid 6/36, high 0/36
- Best cell: chop_high_zone=55/donchian_window=15, QQQ low-vol, Sharpe 2.26
- Best avg-across-regime config: chop_high_zone=70/donchian_window=20, QQQ avg Sharpe 1.166 (only 2 vol-regime cells had trades)

## Single-config validators (chop_high_zone=70, donchian_window=20, chop_window=14, chop_lookback=10, ema_window=50, max_hold_days=30)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.975 near-miss | -0.085 **FAIL** | >= 1.0 |
| Max Drawdown | 0.025 PASS | 0.057 PASS | <= 0.25 |
| TC survival (10bps) | 0.962 PASS | -0.106 **FAIL** | >= 0.5 |
| Walk-forward (4-split manual) | 1.00 PASS | 0.75 PASS | >= 0.75 |
| Parameter sensitivity | 0.191 PASS | 1.452 **FAIL** | <= 0.5 |
| Trade count | **2** | **3** | n/a (informational) |

## Verdict
**REJECTED.** QQQ is a Sharpe near-miss (0.975) but on only **2 full-sample
trades** — statistically meaningless (single-digit trade counts have failed
sanity checks in numerous prior iterations, e.g. TD Combo 2026-09-09-031).
SPY fails decisively across Sharpe, TC-survival, and parameter sensitivity
with only 3 trades. The strict triple-AND gate (falling-edge CI transition
+ EMA uptrend + Donchian breakout, all simultaneous) is too restrictive to
generate a usable signal count over the 2019-2026 sample on either equity
ticker, and crypto is decisively rejected (0/54 grid cells). Confirms the
source's own framing that Choppiness Index works best as a "supporting
role" filter rather than a primary triple-condition gate — combining it
with two more simultaneous conditions (EMA + breakout) over-restricts the
signal.
