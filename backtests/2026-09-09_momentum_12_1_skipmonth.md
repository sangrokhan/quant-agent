# 12-1 Month Momentum (Skip-Month Convention) — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_momentum_12_1_skipmonth.py`
**Source:** https://www.quant-investing.com/news/twelve-months-minus-one-month-momentum-added-to-the-screener-12-1-month-momentum

## Hypothesis

Per quant-investing.com's screener explainer, 12-1 month momentum = price(t
- 1 month) / price(t - 12 months), i.e. trailing 12-month return EXCLUDING
the most recent month (to filter out the well-documented short-term
reversal effect that plain trailing momentum captures unintentionally).
This directly follows up on this repo's already-rejected plain (no
skip-month) 12-month time-series momentum (2026-09-03-012), testing
whether adding the skip-month exclusion rescues the signal.

## Grid test (Step 6)

`param_grid={"lookback_days": [189,252], "skip_days": [10,21]}`, symbols
QQQ/SPY/BTC-USDT/ETH-USDT, `vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **48 total cells, 11 passed (pass_fraction 0.229)**
- By asset class: equity 11/24, **crypto 0/24 (decisive fail)**
- By vol regime: low 8/16, mid 3/16, high 0/16
- Best cell: SPY, lookback_days=189/skip_days=21, low-vol regime, Sharpe 3.00

## Single-config validators

| Config | Symbol | Trades | Sharpe (full) | MDD | TC-survival |
|---|---|---|---|---|---|
| lookback=252/skip=21 (standard) | QQQ | 10 | 0.911 FAIL | **0.286 FAIL** (thr 0.25) | 0.903 PASS |
| lookback=252/skip=21 (standard) | SPY | 17 | 0.704 FAIL | **0.341 FAIL** | 0.687 PASS |
| lookback=189/skip=21 (grid best) | QQQ | 19 | 1.094 PASS | **0.286 FAIL** | 1.077 PASS |
| lookback=189/skip=21 (grid best) | SPY | 23 | 0.893 FAIL | **0.341 FAIL** | 0.869 PASS |
| lookback=189/skip=10 | QQQ | 15 | 1.242 PASS | **0.286 FAIL** | 1.228 PASS |
| lookback=189/skip=10 | SPY | 23 | 0.677 FAIL | **0.341 FAIL** | 0.659 PASS |

## Decision: REJECTED

Max drawdown fails DECISIVELY and IDENTICALLY (0.286 QQQ / 0.341 SPY)
across every lookback/skip_days combination tested — this is a structural
long-only trend-following exposure problem (the position is essentially
"always long during any sustained uptrend regardless of lookback tuning"),
not something a skip-month or lookback adjustment can fix. Even the
best-Sharpe configuration (lookback=189/skip=10, QQQ Sharpe 1.242, clears
the 1.0 threshold) still fails MDD by a wide margin. This confirms the
same structural issue flagged in the predecessor's rejection
(2026-09-03-012): a long-only absolute-momentum position with no vol/trend
regime filter is exposed to full drawdowns during momentum crashes
(e.g. the 2022 rate-hike bear market), and the skip-month convention
(designed to filter short-term reversal noise, not drawdown exposure)
does not address this at all. Crypto failed all 24 grid cells decisively.

No further un-gated 12-month-family time-series momentum variant
recommended; a future revisit would need to add an explicit trend/vol
regime filter (as done successfully elsewhere in this repo, e.g.
2026-09-08-145's valuation-boundary-gated TSMOM, which WAS accepted) rather
than tuning the raw lookback/skip parameters.
