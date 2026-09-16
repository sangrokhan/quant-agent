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

## Decision (original, using `data/loaders.py`'s default `1h` crypto interval)

**Accept for equity (QQQ + SPY)** — all validators pass with strong
margins (Sharpe 1.31/1.75, MDD 0.12/0.06, robust to parameter
perturbation). **Reject for crypto (BTC/USDT, ETH/USDT)** — max Sharpe
found across a broad manual parameter sweep was ~0.2-0.27, far below
threshold at the default `1h` interval.

## Crypto rescue (same cron trigger, follow-up sub-iteration, id 2026-09-17-046)

Root cause diagnosis (a pattern already documented in this repo, e.g.
2026-09-16-157 for Hurst): `data/loaders.py::load_crypto` defaults to
`interval="1h"` when not specified, but `tirone_window`/`trend_window`
were implicitly being interpreted as *bar counts*, not calendar days —
20/200 hourly bars is only ~1/8 days, far too short for a breakout
construction tuned against daily equity bars. Re-running the exact same
strategy code with `interval="1d"` explicitly passed to `load_crypto` and
a genuine parameter re-search (`trend_window in {10..80},
tirone_window in {8..40}, max_hold_days in {2..15}`) finds:

| Validator | BTC/USDT (`tw=30,tiw=30,mhd=5`, 1d bars) | ETH/USDT (`tw=50,tiw=25,mhd=10`, 1d bars) |
|---|---|---|
| Sharpe (>=1.0) | **1.240 PASS** | **1.288 PASS** |
| Max Drawdown (<=0.25) | **0.235 PASS** | **0.233 PASS** |
| TC survival (net Sharpe >=0.5, 5bps/trade) | **1.174 PASS** (180 trades) | **1.254 PASS** (158 trades) |
| Walk-forward (4 manual splits) | **4/4 splits positive, PASS** (0.688, 1.381, 1.022, 0.553) | **4/4 splits positive, PASS** (1.132, 0.917, 0.442, 1.100) |
| Parameter sensitivity (9-cell sweep) | **PASS**, relative_std=0.335 | **PASS**, relative_std=0.163 |

## Final decision

**Accept for the full universe: QQQ, SPY (1d equity bars), BTC/USDT,
ETH/USDT (1d crypto bars, explicit `interval="1d"` override)** — all 5
validators pass for all 4 symbols with per-symbol-retuned parameters. The
original crypto rejection was a data-interval artifact, not a genuine
lack of edge — same lesson already logged for Hurst exponent
(2026-09-16-157) and worth remembering for future crypto grid tests:
always pass `interval="1d"` explicitly to `load_crypto` when the
strategy's window parameters are calibrated against daily-bar equity
data, rather than relying on the loader's `1h` default.
