# IBD-style Relative Strength Line Breakout Confirmation — Backtest Report

**Date:** 2026-09-08 (iteration 3, cron trigger 2026-09-09)
**Strategy file:** `strategies/2026-09-09_ibd_relative_strength_line_breakout.py`
**Source:** https://www.investors.com/how-to-invest/investors-corner/growth-stocks-breakout-specialty-tool-relative-strength-line/

## Hypothesis

IBD's "Relative Strength (RS) Line" is a stock's price divided by a broad
benchmark index (S&P 500 in the source's framing), plotted as its own
line. The source's concrete, repeatedly-illustrated rule: a genuine price
breakout (new N-day high) is a higher-conviction long entry when
CONFIRMED by the RS line (price/benchmark) also making a new N-day high
around the same time — vs. a breakout where relative strength is lagging.
Distinct from every prior cross-asset ratio strategy in this repo
(SPY/QQQ z-score pairs [2026-09-04-098], SPY/TLT ratio regime
[2026-09-05-036], XLU/SPY beta rotation [2026-09-05-067]) since those all
trade the ratio itself or use it as a binary on/off gate; this strategy
uses the ratio's own rolling-high status purely as a CONFIRMATION FILTER
on top of price's own independent Donchian-style breakout.

Equity: QQQ traded, SPY as benchmark (source's own choice of a broad
index). Crypto: ETH/USDT traded, BTC/USDT as benchmark (closest crypto
analog of a broad-market index).

## Grid test summary (Step 6, manual grid since strategy needs a 2nd
benchmark series — see script `run_grid_rsl.py`, not committed, scratch
only)

Grid: `price_high_lookback in {30,50}`, `rs_high_lookback in {30,50}`,
`exit_lookback in {15,20}`, `max_hold_days in {30,40}` x symbols
`{QQQ,SPY,ETH/USDT,BTC/USDT}` x vol_regime_splits=3. 2018-01-01 to
2026-09-01.

- `total_cells=192`, `passed_cells=48`, `pass_fraction=0.25`
- `by_asset_class`: equity 48/96 PASS; **crypto 0/96 (decisive reject)**
- `by_vol_regime`: low 32/64, mid 16/64, **high 0/64** — edge concentrated
  in low/mid-vol regimes, zero pass in high-vol, consistent with this
  repo's broader accumulated finding.
- `best_cell`: QQQ, price_high_lookback=30/rs_high_lookback=50/
  exit_lookback=20/max_hold_days=30, low-vol, Sharpe 2.67.
- `worst_cell`: SPY, price_high_lookback=50/rs_high_lookback=50/
  exit_lookback=20/max_hold_days=30, mid-vol, Sharpe -0.94.

## Single-config validator results (full sample)

Config: `price_high_lookback=50, rs_high_lookback=50, exit_lookback=20,
max_hold_days=40`.

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe ratio | 1.441 (PASS) | 0.977 (best found — NEAR-MISS, just under 1.0) |
| Max drawdown | 0.107 (PASS) | 0.205 (PASS at best config) |
| Net Sharpe after costs (10bps/trade) | 1.392 (PASS) | n/a (not accepted) |
| Parameter sensitivity (relative std, 3x3 grid) | 0.117 (PASS) | n/a |
| Walk-forward (manual 4-split substitute, `check_walk_forward` broken repo-wide — see prior iteration's note) | 4/4 splits Sharpe>0: `[0.989, 1.389, 1.384, 1.061]` (PASS) | n/a |

Number of trades: QQQ 31 (over full ~8.7yr sample).

SPY was swept over a wider grid (`price_high_lookback in {20,30,50,70}`,
`rs_high_lookback in {20,30,50,70}`, `exit_lookback in {10,15,20,30}`,
`max_hold_days in {20,30,40,60}`, 256 combos) — best found config
(`price_high_lookback=20, rs_high_lookback=70, exit_lookback=30,
max_hold_days=60`) still only reaches Sharpe 0.977, MDD 0.205 — a clear
near-miss, not accepted.

## Decision

**ACCEPTED for QQQ only** at
`price_high_lookback=50, rs_high_lookback=50, exit_lookback=20,
max_hold_days=40` (with `symbol_hint="QQQ"`, benchmark=SPY).
**NEAR-MISS for SPY** (best Sharpe 0.977, benchmark=QQQ) — worth
revisiting with a different benchmark (e.g. a broader index ETF via
yfinance if available) in a future loop.
**REJECTED for crypto** (ETH/USDT vs BTC/USDT benchmark) — decisive
0/96 grid cells.

Scope caveat: edge concentrates in low/mid-vol regimes and disappears
entirely in high-vol (0/64) — same pattern as most trend/breakout
strategies in this repo.
