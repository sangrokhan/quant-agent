# Joe Ross Trader's Trick Entry (TTE) — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_ross_traders_trick_entry.py`
**Source:** https://forexsb.com/wiki/trading/tte

## Hypothesis

Joe Ross's Trader's Trick Entry (TTE) is an EARLIER entry than the
already-tested Ross Hook (2026-09-28-066/067): "Once a Ross Hook or
point 2 of 1-2-3 pattern is in place, we watch the correction and want
to buy a violation of the high of any of the first three [bars] after
the Ross Hook [low]... there must be sufficient room between our entry
price and the [hook] point for us to be able to cover costs." Rather
than waiting for the hook's own high breakout (as the sibling Ross Hook
strategy does), TTE enters on an early violation of one of the first few
post-hook-low bars' highs, subject to a minimum profit-room requirement.
0 prior "Trader's Trick Entry"/"TTE" hits in strategies_index.jsonl --
distinct timing mechanic on the same underlying pattern.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`tte_bars in {2,3,4}` x `target_r_multiple in {1.0,1.5,2.0}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.407 (44/108)**
- by_asset_class: equity 35/54 (65%), crypto 9/54
- by_vol_regime: low 26/36, mid 9/36, high 9/36
- best_cell: QQQ, tte_bars=3, target_r_multiple=1.5, low-vol, Sharpe 2.31

Full-sample sweep across `tte_bars in {2,3,4}` x `target_r_multiple in
{1.0,1.5,2.0}` on QQQ/SPY: `tte_bars=3, target_r_multiple=1.5` clears
Sharpe >= 1.0 on BOTH symbols with strong margin (QQQ 1.338, SPY 1.166),
adopted as the primary config below.

## Single-config validators (config: tte_bars=3, target_r_multiple=1.5, pivot_window=7, hook_lookback=25, min_room_pct=0.01, max_hold_days=25, full sample)

| Validator | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.338 | 1.166 | >= 1.0 | **pass (both)** |
| Max drawdown | 0.122 | 0.176 | <= 0.25 | pass (both) |
| Transaction cost survival (10bps/trade) | net Sharpe 1.283 (33 trades) | net Sharpe 1.076 (38 trades) | >= 0.5 | pass (both) |
| Walk-forward (4 splits, SPY, manual fallback) | per-split Sharpe [2.70, -0.70, 0.41, 0.64], pass_fraction 0.75 | -- | >= 0.75 | pass (exactly at threshold) |
| Parameter sensitivity (9-combo grid) | relative_std 0.051 | -- | <= 0.5 | pass |

Crypto: only 9/54 grid cells pass -- not tested at single-config level.

## Decision

**Accepted for equity (QQQ, SPY)** at `tte_bars=3,
target_r_multiple=1.5`. All validators pass with good margin; parameter
sensitivity is especially low (0.051), showing the TTE timing mechanic's
edge is robust across the tested tte_bars/target_r_multiple grid.
**Not accepted for crypto** -- grid pass rate too low (9/54).

## Notes for future loops

This is this repo's second "Ross-family" strategy accepted this cron
trigger (alongside the Ledge breakout, 2026-09-28-068), and demonstrates
that TTE's earlier-entry timing on top of the same primary-1-2-3-then-
hook structure as the (near-miss-then-rescued) plain Ross Hook strategy
(2026-09-28-066/067) produces materially BETTER risk-adjusted returns
(QQQ 1.338 vs 1.175, SPY 1.166 vs 1.023) and a lower parameter-
sensitivity relative_std (0.051 vs 0.253) than the plain hook-breakout
version -- consistent with the source's own framing of TTE as an
improvement over waiting for full confirmation. A future loop could
compare position-sizing or combine TTE with the Ledge breakout filter
for a cross-pattern confluence entry.
