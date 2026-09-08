# 200-SMA Percent-Distance Hysteresis Trend-Following — Backtest Report

**Date:** 2026-09-08 (iteration 7, cron trigger 2026-09-09)
**Strategy file:** `strategies/2026-09-09_sma200_pct_distance_hysteresis.py`
**Source:** https://kr.tradingview.com/script/QEVAQHl6-SPY-200SMA-4-Entry-3-Exit-Strategy-QQQ-TQQQ/

## Hypothesis

Adapted from a TradingView LETF-rotation script (stripped of its
leveraged-ETF/TQQQ mechanics, which this repo's SAFETY.md and loaders.py
don't support): price crossing meaningfully ABOVE its N-day SMA (not
simply close>SMA) is a stronger trend-confirmation entry, and exiting
only once price drops meaningfully BELOW the SMA (not simply close<SMA)
avoids getting shaken out during a still-intact uptrend. Source's own
explicit asymmetric design: +4% entry threshold vs -3% exit threshold.
Distinct from the already-tested plain 200-SMA price-position rule
(2026-09-04-074, no percentage offset at all) and every ADX/efficiency-
ratio-gated 200-SMA variant since this uses PERCENTAGE DISTANCE from the
SMA as the sole mechanism, with deliberately asymmetric thresholds
creating a wide hysteresis band.

## Grid test summary (Step 6)

Grid: `sma_window in {150,200}`, `entry_pct_threshold in {0.02,0.04,0.06}`,
`exit_pct_threshold in {-0.02,-0.03,-0.05}` x symbols
`{QQQ,SPY,BTC/USDT,ETH/USDT}` x vol_regime_splits=3. 2018-01-01 to
2026-09-01.

- `total_cells=216`, `passed_cells=58`, `pass_fraction=0.269`
- `by_asset_class`: equity 58/108 PASS; **crypto 0/108 (decisive reject)**
- `by_vol_regime`: low 36/72, mid 18/72, high 4/72.
- `best_cell`: QQQ, sma_window=150/entry=0.04/exit=-0.03 (the source's
  own exact stated thresholds), low-vol, Sharpe 2.55.

## Single-config validator results (full sample)

| Metric | QQQ (`sma_window=200,entry=0.02,exit=-0.05`) | SPY (`sma_window=200,entry=0.01,exit=-0.02`) |
|---|---|---|
| Sharpe ratio | 1.247 (PASS) | 1.195 (PASS) |
| Max drawdown | 0.183 (PASS) | 0.116 (PASS) |
| Net Sharpe after costs (10bps/trade) | 1.241 (PASS) | 1.179 (PASS) |
| Parameter sensitivity (relative std, 3x3 grid) | 0.080 (PASS) | 0.200 (PASS) |
| Walk-forward (manual 4-split substitute) | `[0.850, inf, 1.985, 1.097]` (3 finite splits all positive; PASS) | `[0.647, -0.894, 1.701, 1.408]` (3/4 positive = 0.75, PASS at threshold) |

**Important caveat:** QQQ's number of trades over the full ~8.7yr sample
is only **6** — this is an extremely low-frequency strategy (entries only
fire on genuinely large, sustained trend moves given the wide hysteresis
band). All validator metrics technically pass, but with only 6 trades the
statistical confidence in the Sharpe/MDD figures is much weaker than for
higher-frequency strategies in this repo; one of the walk-forward splits
even produced an `inf` Sharpe (a degenerate case from a single-trade
slice with a small/zero return-series variance in that sub-period,
excluded from the pass/fail count as non-finite). SPY has a more
reasonable 11 trades. Treat QQQ's acceptance here as lower-confidence
than typical, and worth a future loop's fresh re-derivation with a larger
out-of-sample window once more data accumulates.

## Decision

**ACCEPTED for equity (QQQ, SPY)** — per-symbol tuned configs.
**REJECTED for crypto** (BTC/USDT, ETH/USDT) — decisive 0/108 grid cells.

Scope caveat: this is a very-low-frequency trend-following overlay;
QQQ's 6-trade sample size is a genuine statistical-confidence weakness
flagged for future revisit, not swept under the rug.
