# Backtest Report: Fractional-ATR-Distance Breakout, Fixed-Bar Exit

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_fractional_atr_breakout_fixedbar.py`
**Source:** https://statoasis.com/overfit/research/same-breakout-strategy-different-results-nasdaq-vs-sp500-vs-dow (Ali Casey / StatOasis, visited via `browser_exec`)

## Hypothesis

A deliberately minimal long-only breakout: entry when today's high clears
prior close + a small fractional-ATR distance (0.25x ATR(10), much smaller
than the 1.5-3x multiples typical of Turtle/Chande-Kroll breakouts already
tested), held for exactly a fixed number of bars with NO stop-loss and NO
profit target -- the source's own explicitly minimal design.

## Grid Test Summary (Step 6)

`param_grid={"atr_frac": [0.15,0.25,0.5], "hold_days": [3,5,10]}`,
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Total cells:** 108, **passed:** 24, **pass_fraction:** 0.222
- **By asset class:** equity 24/54 (0.444), crypto 0/54 (0.0)
- **By vol regime:** low 18/36 (0.50), mid 6/36 (0.167), high 0/36 (0.0)
- **Best cell:** equity/SPY, low-vol, `atr_frac=0.15, hold_days=10`,
  Sharpe 2.92
- Best full-sample-averaged equity config: `atr_frac=0.25, hold_days=10`
  (avg equity Sharpe 1.29)

## Single-Config Validation (Step 7) — `atr_frac=0.25, hold_days=10`

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd (4-split) | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.093 (PASS) | 0.356 (FAIL, decisive) | 0.906 (PASS) | 1.00 (PASS) | 0.160 (PASS) |
| SPY | 1.045 (PASS) | 0.285 (FAIL, near-miss) | 0.809 (PASS) | 1.00 (PASS) | 0.181 (PASS) |
| BTC/USDT | 0.788 (FAIL) | 0.784 (FAIL, decisive) | 0.729 (PASS) | 1.00 (PASS) | 0.183 (PASS) |

## Decision (Step 8): **REJECTED**

Both equity symbols clear the Sharpe bar comfortably (1.05-1.09) with
excellent parameter stability (relative std 0.16-0.18, among the most
robust seen this cron trigger) -- but the strategy's complete absence of
any stop-loss mechanism (exactly as the source specified: "no stop loss")
means max-drawdown fails on QQQ decisively (0.356) and on SPY at a
near-miss (0.285 vs 0.25). BTC/USDT fails catastrophically on drawdown
(0.784) as expected for an unstopped breakout in a much more volatile
asset. This is a genuinely strong-looking signal (Sharpe, walk-forward,
and parameter sensitivity all excellent) let down entirely by the bare
rule's missing risk control -- worth a direct follow-up iteration adding
a hard ATR-multiple stop-loss (the obvious, source-independent fix this
repo has used successfully elsewhere, e.g. Turtle System 1) to see if
tail-risk containment alone rescues the drawdown without hurting the
otherwise-strong Sharpe/robustness profile.
