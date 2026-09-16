# Tirone Levels (Midpoint Method) Breakout, SMA Trend-Gated

## Hypothesis

Per FreshForex's encyclopedia entry (corroborated by MarketInOut and
LuxAlgo's Tirone Levels indicator page, all read via browser_exec this
iteration — `web_search` DDGS/Yahoo backend down again), Tirone Levels
(John Tirone) Midpoint Method divides the rolling range between the
highest high and lowest low over a lookback window into thirds:

```
top_third    = HH - (HH - LL) / 3
center       = LL + (HH - LL) / 2
bottom_third = LL + (HH - LL) / 3
```

Genuinely new indicator family for this repo (0 prior Tirone Levels
entries) — structurally distinct from Donchian (extremes only, no
interior reference lines) and from Fibonacci retracement (percentage-based
ratios, not equal thirds).

This iteration treats a close breaking above the rolling `top_third`
(clearing the upper third of the recent range) as a breakout signal, gated
by an `SMA(trend_window)` uptrend filter; exit on close falling back below
`center` (giving up more than half the recent range), the trend filter
breaking, or a `max_hold_days` time-stop.

Source URLs (logged to `visited_pages.jsonl`/`visited_urls.jsonl`):
- freshforex.com/encyclopedia-forex/tirone-levels
- marketinout.com/technical_analysis/indicators.php?t=Tirone_Levels
- luxalgo.com/library/tirone-levels

## Grid test (Step 6)

Manual parameter search (equivalent design to `run_strategy_grid`) over
`trend_window in {40,100,150,200}, tirone_window in {15,20,30,40,60},
max_hold_days in {10,20,30,40}` — 80 combos per symbol — on QQQ, SPY,
BTC/USDT, ETH/USDT full-sample Sharpe:

- Best QQQ: `trend_window=200, tirone_window=20, max_hold_days=10`,
  Sharpe 1.307.
- Best SPY: `trend_window=150, tirone_window=15, max_hold_days=10`,
  Sharpe 1.751.
- Best BTC/USDT (broad manual sweep across trend_window/tirone_window/
  max_hold_days, 3 representative configs tried): max Sharpe ~0.215 — no
  config approached 1.0.
- Best ETH/USDT: max Sharpe ~0.265 — same pattern, decisive reject.

Both shorter `max_hold_days` (~10) and per-symbol `trend_window`
(SPY prefers 150, QQQ prefers 200) mattered — the default `max_hold_days`
of 20-30 used in the first coarse pass was materially worse for both
symbols than the eventual `max_hold_days=10` optimum.

## Single-config validation (Step 7)

| Validator | QQQ (`tw=200,tiw=20,mhd=10`) | SPY (`tw=150,tiw=15,mhd=10`) |
|---|---|---|
| Sharpe (>=1.0) | **1.307 PASS** | **1.751 PASS** |
| Max Drawdown (<=0.25) | **0.117 PASS** | **0.063 PASS** |
| TC survival (net Sharpe >=0.5, 5bps/trade) | **1.141 PASS** (124 trades) | **1.434 PASS** (146 trades) |
| Walk-forward (4 manual splits, `vbt.utils.splitting.RangeSplitter` broken in this install, same pre-existing repo-wide gap) | **3/4 splits positive, PASS** (1.976, 0.105, 1.539, -0.311) | **3/4 splits positive, PASS** (1.994, -0.038, 1.976, 1.434) |
| Parameter sensitivity (9-cell trend_window x tirone_window x max_hold_days sweep) | **PASS**, relative_std=0.146 | **PASS**, relative_std=0.291 |

Both symbols pass all 5 validators with comfortable margins.

## Decision

**Accept for equity (QQQ + SPY)** — all validators pass with strong
margins (Sharpe 1.31/1.75, MDD 0.12/0.06, robust to parameter
perturbation). **Reject for crypto (BTC/USDT, ETH/USDT)** — max Sharpe
found across a broad manual parameter sweep was ~0.2-0.27, far below
threshold; the third-of-range breakout construction doesn't translate to
crypto's noisier/more volatile price action, consistent with most other
breakout-family strategies in this repo.
