# Backtest Report: Larry Williams' Smash Day Reversal

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_smash_day_reversal.py`
**Source:** Larry Williams' "Smash Day" pattern (Google AI-overview synthesis + The Rogue Quant Substack "I Backtested Larry Williams' Trading Strategy Across 15 Markets"; visited via `browser_exec` this iteration; `web_search` failed several queries with rustls TLS-EOF errors requiring the browser fallback)

## Hypothesis

A "Smash Day" occurs when today's close breaks below yesterday's low --
a violent one-day overshoot to the downside. Rather than buy the Smash
Day itself, the classic rule places a buy-stop at the Smash Day's own
high: if the next session rallies enough to clear that high, it confirms
the overshoot was a false move and triggers a long entry. Exit uses the
Smash Day's own low as a structural stop. First Smash Day pattern tested
in this repo.

## Grid Test Summary (Step 6)

`param_grid={"target_r_mult": [1.5,2.0,3.0], "max_hold_days": [10,15,25]}`,
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Total cells:** 108, **passed:** 26, **pass_fraction:** 0.241
- **By asset class:** equity 25/54 (0.463), crypto 1/54 (0.019)
- **By vol regime:** low 18/36 (0.50), mid 8/36 (0.222), high 0/36 (0.0)
- **Best cell:** equity/QQQ, low-vol, `target_r_mult=3.0, max_hold_days=15`,
  Sharpe 2.24
- Best full-sample-averaged equity config: `target_r_mult=3.0,
  max_hold_days=15` (avg equity Sharpe 0.925)

Same pattern as most of this repo's mean-reversion/reversal strategies:
strong in low-vol, essentially absent in high-vol regime (0/36 cells).

## Single-Config Validation (Step 7) — `target_r_mult=3.0, max_hold_days=15`

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd (4-split) | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.675 (FAIL) | 0.430 (FAIL) | 0.508 (PASS, barely) | 0.75 (PASS) | 0.269 (PASS) |
| SPY | 0.613 (FAIL) | 0.253 (FAIL) | 0.417 (FAIL) | 0.75 (PASS) | 0.296 (PASS) |
| BTC/USDT | 0.599 (FAIL) | 0.566 (FAIL) | 0.553 (PASS) | 1.00 (PASS) | 0.221 (PASS) |

## Decision (Step 8): **REJECTED**

Fails Sharpe on all three symbols tested (0.60-0.68, well short of the 1.0
threshold) and fails max-drawdown decisively on all three (0.25-0.57 vs
0.25 threshold) -- this is a clean rejection, not a near-miss. The pattern
fires frequently (150-180 trades over the sample) but the structural
stop (Smash Day's own low) is evidently too loose relative to the modest
profit target, producing an unfavorable risk/reward that shows up as both
weak risk-adjusted return and outsized drawdowns, especially on crypto
(MDD 0.566). The grid's own vol-regime breakdown confirms the edge, such
as it is, only shows up in low-vol conditions and disappears entirely in
high-vol (0/36 passing cells) -- consistent with this being a fragile,
regime-dependent pattern rather than the durable classic its reputation
suggests when tested plainly (without Larry Williams' own often-undisclosed
additional filters, e.g. trend context or seasonal timing, which the
sources referenced this iteration did not fully specify).
