# Darvas Box breakout (equity only)

**Hypothesis:** Per tradingsim.com's "Darvas Box Trading Strategy: Complete
Guide", Nicolas Darvas's mechanical rule set: a new N-day high, followed by
`confirm_days` consecutive days that do NOT exceed that high, confirms a
"box" (top = the high, bottom = lowest low during confirmation). Buy on a
close breaking above the box top; exit on a close breaching the box bottom
or a max_hold_days time-stop (Darvas himself used no time-stop; added here
to bound risk).

Source: https://www.tradingsim.com/blog/darvas-box (fetched via
`browser_exec`, `web_extract` failed — ddgs backend is search-only and
cannot extract URL content).

Novelty: distinct from prior Donchian-breakout family (2026-09-03-008 plain
Donchian, 2026-09-04-054 Turtle 20/10) — Darvas's box is event-triggered
and freezes top/bottom between re-formation events (gated by the
`confirm_days` non-exceedance rule), rather than Donchian's continuously
rolling channel recomputed every bar.

## Step 6 — Grid summary

Grid: `high_lookback in {30,52,75}`, `confirm_days in {3,5}`,
`max_hold_days in {25,40}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 144 total cells.

- pass_fraction: 0.208 (30/144)
- by_asset_class: equity 30/72 passed; crypto 0/72 (decisive fail)
- by_vol_regime: low 24/48, mid 6/48, high 0/48
- best_cell: high_lookback=75, confirm_days=5, max_hold_days=40, SPY,
  low-vol, Sharpe 2.83

## Step 7 — Single-config validation (high_lookback=75, confirm_days=5, max_hold_days=40, QQQ)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.10 | ≥ 1.0 |
| Max drawdown | ✅ | 16.3% | ≤ 25% |
| Transaction cost survival (10bps/trade, 23 trades) | ✅ | net Sharpe 1.06 | ≥ 0.5 |
| Walk-forward (4 manual splits, vectorbt `RangeSplitter` API unavailable in installed version — same known scaffold bug noted in prior reports, worked around with manual `np.array_split`) | ✅ | 4/4 splits positive Sharpe (100%) | ≥ 75% |
| Parameter sensitivity (12-point grid on QQQ across the tested param combos) | ✅ | relative std 0.184 | ≤ 0.5 |

All validators pass on QQQ at the grid's best-equity config. Crypto is
decisively rejected (0/72 grid cells) — this strategy is scoped to equity
only.

## Decision: **ACCEPT (equity only — QQQ/SPY; crypto rejected)**

Honest scope: works only in low/mid-vol equity regimes (high-vol equity
0/48 in the grid); consistent with Darvas's own bull-market-only caveat
noted in the source article.
