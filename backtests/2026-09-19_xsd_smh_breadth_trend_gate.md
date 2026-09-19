# 2026-09-19 — XSD/SMH Semiconductor Breadth Trend Gate (SPY) — ACCEPTED

## Hypothesis

Per Theta Nerd's "Semiconductor Signals" dashboard
(https://thetanerd.com/semiconductors/semiconductor-signals/): the XSD/SMH
ratio (small-cap semiconductor ETF vs mega-cap-weighted semiconductor ETF)
measures market breadth *within* the semiconductor complex. Source framing:
"XSD/SMH rising = breadth expanding, small-caps participating — healthy
rally" vs "falling = narrow leadership, mega-caps only — watch for
exhaustion." Adapted as a trend-confirmation gate: stay long the primary
index only while its own SMA trend is intact AND the XSD/SMH ratio is
at/near its own trailing rolling high (breadth is healthy), flat otherwise.

Distinct from the already-tested/saturated SOXX/QQQ semiconductor-
leadership-vs-broad-tech signal (2026-09-09-118/119/120) — that measures
semis-vs-broad-tech momentum; this measures breadth *within* semis
(small-cap vs mega-cap), a different relationship from the same dashboard.

## Primary config (best grid cell)

`asset_class="equity", trend_window=30, ratio_lookback_weeks=10, near_high_tolerance=0.02` on **SPY**.

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.32 | >= 1.0 |
| Max drawdown | PASS | 0.080 | <= 0.25 |
| Transaction cost survival (5bps/trade, 100 trades) | PASS | net Sharpe 1.16 | >= 0.5 |
| Walk-forward (4 manual equal splits — `check_walk_forward`'s `vbt.utils.splitting.RangeSplitter` still broken in vectorbt 1.1.0, pre-existing repo issue) | PASS | 4/4 splits positive Sharpe (1.0 frac) | >= 0.75 |
| Parameter sensitivity (9-cell trend_window x ratio_lookback_weeks sweep around SPY) | PASS | relative std 0.11 | <= 0.5 |

## Grid-test summary (Step 6)

Grid: `trend_window in {30,50,75} x ratio_lookback_weeks in {10,20,30}`,
symbols `{QQQ, SPY} x {BTC/USDT, ETH/USDT}`, 3 realized-vol terciles
(low/mid/high), 2019-01-01 to 2026-09-01.

- Overall: 39/108 cells passed (pass_fraction 0.361)
- By asset class: equity 24/54 (0.44), crypto 15/54 (0.28)
- By vol regime: low 19/36 (0.53), mid 18/36 (0.50), high 2/36 (0.06) —
  strategy strongly regime-dependent, degrades sharply in high-vol terciles
  (expected: the ratio-rolling-high gate + SMA trend filter both tend to
  flip flat during high-vol drawdowns, which is by design but means the
  live edge is concentrated in calmer regimes).
- Best single-param SPY combo: `trend_window=30, ratio_lookback_weeks=10`
  passed all 3 vol-regime cells (3/3), Sharpes [1.54, 1.13, 1.48] across
  low/mid/high — the one param combo that held up in the high-vol tercile
  too, hence selected as primary config.
- QQQ was a near-miss at the same params (2/3 cells passed, Sharpes
  [1.9, 1.9, 0.53]) — high-vol tercile failed for QQQ specifically.
- Crypto (BTC/ETH, ratio gate always True i.e. plain SMA trend-follow
  fallback) was weaker overall (15/54, 0.28) — best crypto cell was
  ETH/USDT trend_window=50/ratio_lookback_weeks=10 mid-vol, Sharpe 2.91,
  but crypto did not hold up as consistently as SPY across regimes.

## Scope / honesty note

Accepted for **SPY only** at `trend_window=30, ratio_lookback_weeks=10`.
QQQ is a near-miss (fails high-vol tercile) and crypto degrades to a plain
SMA trend-follow (no small-cap/mega-cap semiconductor-ETF analogue exists
in crypto) with weaker, less-robust performance — do not treat this as a
universally-accepted strategy across all asset classes/tickers.

## Sources visited this iteration

- https://thetanerd.com/semiconductors/semiconductor-signals/ (useful — yielded this hypothesis)
- https://www.spy-signal.com/semiconductor (not useful — plain 200-SMA leveraged rotation tracker, no novel rule)

Both accessed via `browser_exec` (web_extract failed: DuckDuckGo backend
cannot extract URL content, "search-only backend" error) — normal fallback
per RESEARCH_LOOP.md Step 2.
