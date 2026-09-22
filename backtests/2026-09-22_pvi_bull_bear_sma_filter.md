# Backtest Report: Positive Volume Index (PVI) 255-day-SMA Bull/Bear Filter (Fosback)

**Strategy file:** `strategies/2026-09-22_pvi_bull_bear_sma_filter.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-063

## Hypothesis

Per the Google AI overview summarizing Norman Fosback's classic PVI rule
(https://www.google.com/search?q=Positive+Volume+Index+PVI+Quantified+Strategies+trading+rules,
read via browser_exec -- web_search's DDGS backend intermittently
TLS-erroring; both quantifiedstrategies.com's and arrowalgo.com's
PVI-specific article URLs 404'd, so only the AI-overview summary and
secondary snippet sources were usable), the Positive Volume Index (PVI) is
a cumulative index updating its percentage price change only on days when
volume exceeds the prior day's volume. Fosback's rule: go long when PVI is
above its 255-day SMA (bull regime), exit to cash when PVI falls below its
255-day SMA (bear regime). First PVI-as-primary-signal test in this repo (0
prior KB hits for "Positive Volume Index"; NVI mentioned 2-3x only as a
companion concept, never itself the primary tested signal).

## Grid Test Summary (Step 6)

- Total cells: 36 (3 pvi_sma_window values [150,200,255], 3 vol regimes,
  QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.083 (3/36)
- By asset class: equity 3/18, crypto 0/18
- By vol regime: low 0/12, mid 3/12, high 0/12
- Best cell: ETH/USDT, pvi_sma_window=150, mid-vol regime, Sharpe 1.87 (but crypto overall 0/18 elsewhere)
- Worst cell: QQQ, pvi_sma_window=150, high-vol regime, Sharpe -1.07

## Single-Config Validation (Step 7), QQQ, pvi_sma_window=150

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **false** | 0.115 | 1.0 |
| Max drawdown | true | 0.181 | 0.25 |
| Transaction cost survival (10bps/trade, 14 trades) | **false** | net Sharpe 0.085 | 0.5 |
| Walk-forward (manual 4-equal-slice) | **false** | 2/4 splits positive (0.5) | 0.75 |
| Parameter sensitivity (3-value sweep) | **false** | relative std 0.504 | 0.5 |

## Outcome: REJECTED

4 of 5 validators fail decisively. Full-sample Sharpe on QQQ (0.115) is far
below threshold despite 3 grid cells nominally passing -- those passes were
isolated to the mid-vol-regime tercile only (low and high-vol regimes 0/12
each), and even the "best cell" (ETH/USDT Sharpe 1.87) did not generalize:
crypto overall passed 0/18 cells. This is consistent with Fosback's PVI
being designed as a slow macro regime filter (255-day SMA of a cumulative
index) rather than a standalone daily-bar tradable signal -- the source
material itself explicitly cautions "it is only an indicator and cannot be
a strategy on its own; you must combine it with price action" (per one of
the Google SERP snippets). A future iteration could revisit PVI as a
regime-gate layered on top of another primary signal (e.g. combined with
NVI dual-confirmation as the source also mentions) rather than as the sole
entry/exit trigger.
