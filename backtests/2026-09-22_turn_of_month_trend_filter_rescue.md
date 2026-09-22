# Backtest Report: Turn-of-the-Month + SMA(200) Trend Filter (rescue of 2026-09-22-065)

**Strategy file:** `strategies/2026-09-22_turn_of_month_trend_filter_rescue.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-066

## Hypothesis

Direct rescue attempt for this same cron trigger's prior near-miss
2026-09-22-065 (Turn-of-Month Ultimo Effect, QQQ Sharpe 0.895/SPY Sharpe
0.883, both narrowly <1.0, but all other 4/5 validators passed cleanly on
both symbols). Adds the exact fix suggested in that report's own notes:
gate the calendar entry on close > SMA(200) (this repo's standard uptrend
filter) at the moment of entry, skipping turn-of-month trades in
confirmed-downtrend months. Source: QuantifiedStrategies.com's "The Turn
Of The Month Trading Strategy (Ultimo Effect)"
(https://www.quantifiedstrategies.com/turn-of-the-month-trading-strategy/,
originally read via browser_exec in the prior iteration this same cron
trigger).

## Grid Test Summary (Step 6)

- Total cells: 48 (2 entry_days_before_month_end[3,5] x 2 hold_days[5,7], 3
  vol regimes, QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.313 (15/48) -- improved from the un-gated base
  strategy's 0.271 (13/48)
- By asset class: equity 9/24, crypto 6/24
- By vol regime: low 4/16, mid 6/16, high 5/16 (spread remains broad)
- Best cell: SPY, entry_days_before_month_end=3/hold_days=7, low-vol regime, Sharpe 1.99
- Worst cell: BTC/USDT, entry_days_before_month_end=3/hold_days=7, low-vol regime, Sharpe -0.43

## Single-Config Validation (Step 7), entry_days_before_month_end=5/hold_days=7/trend_window=200 (source's exact calendar rule + rescue's trend gate)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | true 1.076 | **false** 0.733 | 1.0 |
| Max drawdown | true 0.131 | true 0.155 | 0.25 |
| Transaction cost survival (10bps/trade, 66 trades) | true net Sharpe 0.936 | true net Sharpe 0.564 | 0.5 |
| Walk-forward (manual 4-equal-slice) | true 3/4 (0.75) | **false** 2/4 (0.5) | 0.75 |
| Parameter sensitivity (4-combo sweep) | true 0.088 | true 0.143 | 0.5 |

## Outcome: ACCEPTED (QQQ only); REJECTED (SPY)

**QQQ: all 5 validators pass** -- the trend-filter rescue works decisively
for QQQ: Sharpe rises from the base strategy's 0.895 near-miss to 1.076
(clears threshold), while MDD, TC-survival, walk-forward (exactly at the
0.75 minimum), and parameter sensitivity all remain comfortably passing.
Trade count drops from 92 (un-gated) to 66 (gated) as expected -- some
turn-of-month windows in the sample fell during QQQ downtrends and are now
correctly skipped.

**SPY: still rejected**, and the trend gate actually made SPY's numbers
*worse* on this exact config (Sharpe 0.733 vs. the un-gated 0.883, and
walk-forward now fails outright at 2/4 vs. the un-gated 4/4) -- the
downtrend months the filter is excluding for SPY were apparently some of
its *better*-performing turn-of-month windows, an asymmetry from QQQ. Kept
in `strategies/` as QQQ-scope live strategy per repo convention (accepted
symbols only); the un-gated 2026-09-22-065 remains the better (though
still rejected) choice specifically for SPY.

**Scope**: this strategy is ACCEPTED for QQQ only. SPY and both crypto
symbols (BTC/USDT, ETH/USDT -- not separately validated at the single-config
level this iteration, but grid crypto pass rate 6/24 with no crypto cell
anywhere near the sample-level Sharpe/TC bar) are out of scope; a future
loop should not assume this config generalizes beyond QQQ.
