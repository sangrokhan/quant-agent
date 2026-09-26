# Backtest Report: Declining High/Low 3-Day Streak + RSI(2)>70 Exit (2026-09-26)

**Strategy file:** `strategies/2026-09-26_declining_hl_streak_rsi2_exit.py`
**KB id:** 2026-09-26-015

## Hypothesis

Per a Google AI-overview synthesis of QuantifiedStrategies.com's
"Consecutive Down Days Strategy" content
(quantifiedstrategies.substack.com/consecutive-down-days-strategy):
close>SMA(200) trend filter + 3 consecutive days where each day's HIGH
AND LOW are both lower than the prior day's high/low (a stricter pattern
than a close-only down-streak) triggers a long entry at the qualifying
day's close; exit when RSI(2) rises above 70. Distinct from the 3 prior
Consecutive-Down-Days entries in this repo (2026-09-08-058,
2026-09-20-065, 2026-09-22-121), all of which use close-only or
close-vs-SMA(5) streak definitions and different exits (SMA(5) cross or
prior-close cross, not RSI(2) threshold).

## Grid test (Step 6)

`down_streak_days` in {2, 3, 4} x `exit_threshold` in {60, 70, 80},
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3,
2016-2026 (108 cells):

- pass_fraction = 0.111 (12/108)
- by_asset_class: equity 10/54, crypto 2/54
- by_vol_regime: low 11/36, mid 0/36, high 1/36
- best_cell: `down_streak_days=2, exit_threshold=80`, QQQ, low-vol,
  Sharpe 1.588
- worst_cell: `down_streak_days=4, exit_threshold=60`, ETH/USDT, mid-vol,
  Sharpe -0.853

Full local 9-combo sweep on QQQ/SPY full 2016-2026 sample:

| Symbol | Best full-sample Sharpe | Best config |
|---|---|---|
| QQQ | 0.773 | down_streak_days=3, exit_threshold=60 |
| SPY | 0.602 | down_streak_days=3, exit_threshold=60 |

## Decision

**REJECT (all symbols, all tested configs)**. Consistent with this cron
trigger's other two rejected pullback-family strategies today
(2026-09-26-013, -014), the grid's low-vol-tercile cells looked attractive
(Sharpe up to 1.59) but full-sample validation is decisive across the
board — best achievable Sharpe is 0.773 (QQQ), well short of 1.0. The
stricter high-AND-low declining-bar pattern (vs a simpler close-only
streak) does not produce a materially better edge than this repo's
already-tested close-only Consecutive-Down-Days variants, which
themselves were rejected or only narrowly accepted at a much shorter
streak length (2026-09-22-121 accepted at down_streak_days=3 but with a
simpler prior-close exit, not this RSI(2)>70 exit). No new external source
needed to confirm this rejection.

## Source

quantifiedstrategies.substack.com/consecutive-down-days-strategy
(disclosed rule via Google AI-overview synthesis; full substack article
paywalled per this repo's established pattern for QuantifiedStrategies
content) — read via `browser_exec` Google SERP.
