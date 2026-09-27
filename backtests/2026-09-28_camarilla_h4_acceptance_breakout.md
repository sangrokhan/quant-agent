# Camarilla H4 Acceptance Breakout — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_camarilla_h4_acceptance_breakout.py`
**Source:** https://arongroups.co/forex-articles/camarilla-pivot-trading-strategy/

## Hypothesis

Camarilla pivot levels (Nick Scott, 1989) derive H1-H4/L1-L4 from the prior
day's close and H-L range. The source frames H3/L3 as mean-reversion zones
(already tested in this repo, `2026-09-04-119`) and H4/L4 as "structural
extremes" where a genuine momentum breakout can accelerate — but only when
price shows **acceptance** (a full close beyond H4, not an intrabar
touch/snap-back — the source explicitly warns "that's where traps live").
This strategy trades the opposite (trend-following breakout) side of the
same indicator: long entry on a fresh close above yesterday's H4 level,
stop at yesterday's H3 level, target = `reward_r_multiple` R, time-stop
`max_hold_days`.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`reward_r_multiple in {1.5,2.0,3.0}` x `max_hold_days in {5,10,15}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.259 (28/108)**
- by_asset_class: equity 27/54, crypto 1/54
- by_vol_regime: low 19/36, mid 8/36, high 1/36
- best_cell: SPY, reward_r_multiple=2.0, max_hold_days=15, low-vol, Sharpe 2.88
- worst_cell: BTC/USDT, reward_r_multiple=1.5, max_hold_days=5, mid-vol, Sharpe -1.10

Equity dominates the passing cells; crypto only passes 1/54 (essentially
noise). This mirrors the source's own framing that momentum-breakout logic
needs a market that can genuinely trend/travel — crypto's 24/7, noisier
regime doesn't confirm "acceptance" as cleanly on daily bars.

## Single-config validators (config: reward_r_multiple=2.0, max_hold_days=15, full sample 2019-2026)

| Validator | SPY | QQQ | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.219 | 1.150 | >= 1.0 | **pass (both)** |
| Max drawdown | 0.174 | 0.197 | <= 0.25 | pass (both) |
| Transaction cost survival (10bps/trade) | net Sharpe 0.655 (232 trades) | net Sharpe 0.740 (218 trades) | >= 0.5 | pass (both) |
| Walk-forward (4 splits, SPY) | per-split Sharpe [0.95, 0.80, 1.94, 1.50], pass_fraction 1.0 | -- | >= 0.75 | pass |
| Parameter sensitivity (QQQ, 9-combo grid) | relative_std 0.258 | -- | <= 0.5 | pass |

Crypto (BTC/USDT full sample) Sharpe: -0.027 — decisive fail, consistent
with the grid.

## Decision

**Accepted for equity (QQQ, SPY)**. All validators pass with comfortable
margin at `reward_r_multiple=2.0, max_hold_days=15`: full-sample Sharpe
>1.0, MDD well under 25%, survives a 10bps/trade cost assumption, walk-
forward robust across all 4 splits, and parameter sensitivity is low
(relative std 0.26 across a 9-combo sweep). **Rejected for crypto**
(BTC/USDT, ETH/USDT) — decisive full-sample and grid failure, consistent
with the source's own emphasis that momentum-breakout "acceptance" logic
needs genuine trend/travel that crypto's noisier 24/7 daily bars don't
confirm as cleanly.

## Notes for future loops

This validates the source's explicit framing that Camarilla H4/L4 (breakout)
and H3/L3 (reversion) are two genuinely complementary, both-tradeable
playbooks of the same indicator on equity — this repo's existing H3
mean-reversion entry (`2026-09-04-119`) was accepted on SPY too, so both
directions of this indicator now have a live equity strategy in `strategies/`.
A future loop could try the mirror short-side (L4 breakdown) if the repo's
long-only scope is ever relaxed, or explore combining both H3-reversion and
H4-breakout signals into a single regime-switching strategy.
