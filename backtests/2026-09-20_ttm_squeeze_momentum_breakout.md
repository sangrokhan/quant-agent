# TTM Squeeze Momentum Breakout (BTC/USDT)

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_ttm_squeeze_momentum_breakout.py`
**Source:** [stockcharts.com ChartSchool — TTM Squeeze](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ttm-squeeze) (browser_exec fallback, web_search DDGS backend TLS-errored on the query); corroborating Google SERP AI-overview + snippets (TradingView, TrendSpider, Scribd, Simpler Trading, Aron Groups, TOS Indicators).

## Hypothesis

John Carter's TTM Squeeze: squeeze is "on" when Bollinger Bands (20, 2σ)
sit fully inside the original Keltner Channel formula (20-period MA, 1.5×
ATR). Squeeze "fires" (turns off) when Bollinger Bands expand back outside
the Keltner Channel — Carter's own entry trigger: "buying on the first
green dot after one or more red dots." Direction is set by a momentum
histogram (Donchian-midline/SMA-average delta, smoothed): only take the
long side if momentum is positive at the fire bar. Exit after momentum
turns down for 2 consecutive bars (Carter's "two bars in the new color"
rule) or a `max_hold_days` time-stop (source notes moves "tend to last 8-10
bars").

## Grid test summary (`grid_result_ttm_squeeze_momentum.json`)

- Grid: `kc_atr_mult` ∈ {1.0, 1.5, 2.0} × `max_hold_days` ∈ {8, 10, 12} ×
  symbols {QQQ, SPY, BTC/USDT, ETH/USDT} × 3 vol terciles = 108 cells.
- **pass_fraction: 0.231** (25/108)
- By asset class: **crypto 18/54 passed vs equity 7/54** — unusually,
  this strategy's edge is concentrated in CRYPTO, the opposite pattern
  from most other strategies in this repo (which tend to be equity-only).
- By vol regime: low 13/36, mid 6/36, high 6/36 — more evenly spread across
  regimes than most strategies tested this trigger.
- `kc_atr_mult=1.0` produced zero trades on QQQ full-sample (degenerate —
  too tight a Keltner multiplier for the Bollinger Bands to ever fully
  enclose, so squeeze never triggers) — an `inf`/undefined Sharpe artifact
  in the raw sweep, excluded from consideration.

## Single-config validation (BTC/USDT, kc_atr_mult=2.0, max_hold_days=10, full sample 2017-2026)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.380 | ≥1.0 |
| Max drawdown | ✅ | 0.220 | ≤0.25 |
| Transaction cost survival (15bps/trade, 98 trades) | ✅ | 1.278 net Sharpe | ≥0.5 |
| Walk-forward (4-split manual) | ✅ | 1.0 (4/4 positive) | ≥0.75 |
| Parameter sensitivity (kc_atr_mult×max_hold_days sweep) | ✅ | 0.196 relative std | ≤0.5 |

All 5 validators pass on BTC/USDT full-sample. **Accepted, crypto-scoped**
(equity did not independently clear Sharpe≥1.0 at any full-sample config
tested — QQQ/SPY best full-sample equity result was SPY kc_atr_mult=2.0/
max_hold_days=8 at Sharpe=0.717).

## Notes

- ETH/USDT's best full-sample config (kc_atr_mult=2.0/max_hold_days=8,
  Sharpe=1.07) also clears the bar but was not separately run through the
  full validator suite this iteration — worth a quick follow-up check.
- The momentum-histogram leg uses an SMA-of-delta smoother as an
  approximation of Carter's linear-regression smoothing (see code
  docstring) — a lighter-weight substitute that preserves sign/direction
  without reimplementing a full rolling-linear-regression indicator.
- First TTM Squeeze strategy in this repo — the only strategy here that
  compares two DIFFERENT volatility-band constructions (Bollinger vs.
  Keltner) against each other as the squeeze/fire detector.
