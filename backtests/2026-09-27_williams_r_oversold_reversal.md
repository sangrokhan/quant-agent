# Williams %R Oversold Reversal — Backtest Report

**Strategy file:** `strategies/2026-09-27_williams_r_oversold_reversal.py`
**Date:** 2026-09-27
**Outcome:** ACCEPTED (equity scope only — QQQ/SPY; crypto out of scope)

## Hypothesis

Source: https://quantifiedstrategies.substack.com/p/williams-r-trading-strategy-williams-203
(read 2026-09-27 via browser_exec; web_extract cannot render this Substack page).

Williams %R measures where the close sits within the recent high-low range
(0 = period high, -100 = period low). Source's disclosed rule, backtested on
SPY: enter long at the close when Williams %R < -90 (deep oversold); exit
when either today's close exceeds yesterday's high (strong-reversal-day
"let it run"), or Williams %R closes back above -30. Source tested lookback
periods 2-25 days; ALL were profitable (profit factor >= 1.9), with the
2-day lookback giving the best result. This repo's implementation adds a
10-day time-stop (this repo's convention; source didn't disclose one).

First Williams %R strategy in this repo (0 prior hits for "Williams %R" /
"williams_percent_r" in `strategies_index.jsonl`) — distinct from all prior
RSI/Stochastic/CCI/Ultimate-Oscillator oscillator-threshold strategies
already tried because Williams %R uses pure high-low range positioning with
no internal averaging/smoothing.

## Single-config validators (QQQ, wr_period=2, oversold_level=-90, exit_level=-30, max_hold_days=10)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.733 | >= 1.0 | PASS |
| Max drawdown | 0.112 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 139 trades) | 1.470 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 1.0 (4/4 splits Sharpe>0) | >= 0.75 | PASS |
| Parameter sensitivity (relative std across wr_period x oversold_level x exit_level) | 0.286 | <= 0.5 | PASS |

All 5 validators pass on QQQ with the source's own recommended 2-day
lookback / -90 oversold / -30 exit configuration.

## Step 6 grid summary (wr_period x oversold_level x exit_level, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- Total cells: 144, passed: 40, **pass_fraction = 0.278**
- By asset class: **equity 38/72 passed** (strong); crypto 2/72 (decisive fail)
- By vol regime: low 16/48, mid 4/48, high 20/48 (edge strongest in
  low-vol and high-vol regimes, weaker in mid-vol)
- Best cell: SPY, wr_period=2, oversold_level=-85, exit_level=-30, high-vol
  regime, Sharpe 2.612
- Worst cell: BTC/USDT, wr_period=2, oversold_level=-90, exit_level=-30,
  low-vol regime, Sharpe -1.080
- Top-performing configs cluster on QQQ/SPY with wr_period in {2, 5} and
  either oversold_level (2/3 vol-regime cells passing per config), matching
  the source's own finding that shorter lookbacks work best.

## Decision: ACCEPTED — equity scope only (QQQ, SPY)

All 5 validators pass decisively on the source's own recommended config.
Crypto is scoped OUT (2/72 grid pass, and BTC/USDT worst-cell Sharpe is
negative in the low-vol regime) — this strategy should only be considered
"live" for equity index ETFs (QQQ/SPY), not crypto, per RESEARCH_LOOP.md
Step 6 guidance on recording honest scope rather than over-generalizing.
