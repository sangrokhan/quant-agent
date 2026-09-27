# Piercing Line 2-Candle Reversal — Backtest Report

**Strategy file:** `strategies/2026-09-27_piercing_line_reversal.py`
**Date:** 2026-09-27
**Outcome:** REJECTED

## Hypothesis

Source: https://quantstrategy.io/blog/how-to-interpret-the-piercing-line-candlestick-pattern-for-profitable-trades/
(read 2026-09-27).

Piercing Line is a 2-candle bullish reversal: day 1 bearish, day 2 opens
with a gap DOWN below day 1's close, then closes ABOVE THE MIDPOINT of day
1's body (piercing back into it, but not a full engulfing). Source's
disclosed construction: aggressive entry at close of day 2 (or next open);
stop below the low of the piercing candle. No fixed target disclosed --
this repo uses an R-multiple target (2R) plus a 12-day time-stop.

First Piercing Line strategy in this repo (0 prior hits).

## Single-config validators (SPY, body_mult=0.75, reclaim_frac_min=0.4, reward_r_multiple=2.0, max_hold_days=12)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.151 | >= 1.0 | **FAIL** |
| Max drawdown | 0.049 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 6 trades) | 0.116 | >= 0.5 | **FAIL** |
| Walk-forward (4 splits) | 0.75 (3/4 splits Sharpe>0) | >= 0.75 | PASS (borderline) |
| Parameter sensitivity (relative std across body_mult/reclaim_frac_min/reward_r) | 0.673 | <= 0.5 | **FAIL** |

## Step 6 grid summary (body_mult x reclaim_frac_min x reward_r_multiple, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- Total cells: 96, passed: 20, **pass_fraction = 0.208**
- By asset class: equity 12/48; crypto 8/48 — reasonably balanced
- By vol regime: **low 8/32, mid 12/32, high 0/32** — decisively fails in
  high-vol regime across the board
- Best cell: ETH/USDT, body_mult=0.75, reclaim_frac_min=0.4,
  reward_r_multiple=1.5, mid-vol regime, Sharpe 1.467
- All 4 symbols contribute at least one passing config, but each only at
  1/3 vol-regime cells (the mid-vol-low-vol tercile split), never the full
  3/3

## Decision: REJECTED

Despite a moderate grid pass_fraction (0.208), the single-config validators
on SPY's grid-best-adjacent config decisively fail: Sharpe (0.151) and
net-of-cost Sharpe (0.116) are both far below threshold, and parameter
sensitivity (relative std 0.673) shows the edge collapses under small
parameter perturbations. Trade count is very thin (6 trades over 7.5yr on
SPY), consistent with the source's own note that this pattern "forms very
rarely" — not enough signal density at daily-bar granularity for the
Sharpe/TC bar to clear reliably. High-vol regime fails decisively across
all symbols (0/32), reinforcing that the strategy's apparent grid edge is a
statistical artifact of very few trades rather than a durable signal.
