# Monday 2-Day-Down-Streak Reversal, Signal-Based Exit — QQQ/SPY/BTC/ETH

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_monday_down_streak_reversal.py`
**Outcome:** ACCEPTED (SPY only); near-miss (QQQ, param sensitivity fails narrowly); rejected (crypto)

## Hypothesis

Per QuantifiedStrategies.com's "5 Algorithmic Trading Strategies 2026"
(https://www.quantifiedstrategies.com/algorithmic-trading-strategies/,
Strategy #2, fully disclosed): buy SPY at Monday's close if the market
closed lower for 2 consecutive days; exit when close rises above the
previous day's high. Source reports 1993-2026 SPY backtest: 285 trades,
7.7% CAGR, 11% time in market. Distinct combination from all prior
day-of-week strategies in this repo: 2026-09-08-116 (single down day,
fixed 1-day hold to Tuesday close) and 2026-09-08-135 (3-day streak,
Tue+Wed, no Monday anchor). This uses a 2-day down streak specifically
anchored to Monday, with a signal-based exit (not a fixed hold).

## Grid test (Step 6)

`param_grid`: down_streak_days in [2, 3], max_hold_days in [5, 10, 15]
`symbols`: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
`vol_regime_splits`: 3
Total cells: 72, passed: 16, **pass_fraction: 0.222**

By asset class: equity 16/36 passed, crypto 0/36 (decisive; no weekly
session structure for crypto to exploit the same way).
By vol regime: low 1/24, mid 3/24, high 12/24 -- edge concentrated in
high-vol regime (panic-driven 2-day declines mean-revert more strongly
when volatility is elevated).

Average Sharpe per param combo (equity):
- down_streak_days=2, max_hold_days=5: avg Sharpe 1.215, 4/6 cells pass (BEST)
- down_streak_days=2, max_hold_days=10: avg Sharpe 1.088, 3/6 pass
- down_streak_days=2, max_hold_days=15: avg Sharpe 1.103, 3/6 pass
- down_streak_days=3, max_hold_days=5/10/15: avg Sharpe 0.47-0.66, 2/6 pass each

Best cell: down_streak_days=2/max_hold_days=5, SPY, high-vol, Sharpe 2.12.

## Single-config validation (Step 7), best config down_streak_days=2/max_hold_days=5

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.154 (PASS) | 1.502 (PASS) | >= 1.0 |
| Max drawdown | 0.071 (PASS) | 0.081 (PASS) | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.995 net Sharpe (PASS) | 1.286 net Sharpe (PASS) | >= 0.5 |
| Walk-forward (4 splits) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity | rel_std 0.547 (FAIL, narrow) | rel_std 0.286 (PASS) | <= 0.5 |

## Decision

**ACCEPTED for SPY only** (down_streak_days=2, max_hold_days=5): all 5
validators pass cleanly, with a strong walk-forward result (4/4 splits
positive) and healthy net-of-cost Sharpe (1.29).

**QQQ is a very close near-miss**: Sharpe/MDD/TC/walk-forward all pass
comfortably, but parameter sensitivity narrowly fails (relative std 0.547
vs 0.5 threshold) -- the strategy's Sharpe swings more across the
down_streak_days x max_hold_days grid on QQQ than on SPY. Worth a future
targeted parameter-refinement iteration (narrower neighborhood around
down_streak_days=2/max_hold_days=5) following this repo's established
pattern of rescuing param-sensitivity near-misses (e.g. 2026-09-04-158/159).

**Crypto rejected decisively** (0/36 grid cells) -- expected, no weekly
session/day-of-week structure for 24/7 markets to exploit this way.

## Source

https://www.quantifiedstrategies.com/algorithmic-trading-strategies/
