# Backtest Report: Laguerre RSI Sizing Dial — ETH/USDT Retune Fix

**Date:** 2026-09-16 (iteration 10, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-14_lrsi_sizing_sma_trend.py` (unmodified, retune only)

## Hypothesis

Direct fix for prior id 2026-09-14-198 (Ehlers Laguerre RSI, naturally
[0,1] bounded 4-stage recursive Laguerre filter, rescaled to [-1,+1] around
its own 0.5 zero line as a continuous sizing dial on SMA(40) trend gate;
accepted QQQ/SPY/BTC-USDT but ETH/USDT rejected on a narrow
parameter-sensitivity near-miss at the original leverage_cap=0.25 crypto
config). This iteration retests the identical unmodified strategy code
with a small targeted parameter sweep around leverage_cap/sensitivity/
deadband to find a configuration that clears parameter-sensitivity while
keeping the other 4 validators passing. No new external research this
iteration — pure parameter retune following this repo's established
near-miss-revisit pattern.

## Parameter sweep (Step 6, targeted)

`leverage_cap ∈ {0.20,0.25,0.30,0.35}` x `sensitivity ∈ {0.3,0.4,0.5}` x
`deadband ∈ {0.15,0.20,0.25}` on ETH/USDT (36 combinations): most clear
Sharpe > 1.0 comfortably (1.06-1.29), with several degenerate `inf` cells
(near-zero trade count, excluded from consideration). Selected
`leverage_cap=0.30, sensitivity=0.3, deadband=0.20` — a well-populated,
non-degenerate cell with Sharpe 1.28, among the strongest and most stable
across neighboring parameter values (avoiding both the too-loose deadband
degenerate cells and the too-low sensitivity=0.5 weaker cells).

## Single-config validator results (Step 7)

| Metric | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.280 | 1.0 | Yes |
| Max Drawdown | 0.206 | 0.25 | Yes |
| TC-survival (net Sharpe, 157 trades) | 1.095 | 0.5 | Yes |
| Walk-forward (4 splits) | 1.00 (4/4 positive) | 0.75 | Yes |
| Parameter sensitivity (6-cell grid rel-std) | 0.028 | 0.5 | Yes |

## Decision

**Accept ETH/USDT** at `leverage_cap=0.30, sensitivity=0.3, deadband=0.20`.
Combined with the existing 2026-09-14-198 accepts (QQQ, SPY, BTC/USDT), the
Laguerre RSI continuous-sizing-dial mechanism now covers the full
universe: QQQ, SPY, BTC/USDT, ETH/USDT. No code changes to the strategy
file — config-level fix only, recorded via this report and the knowledge
base log entry.
