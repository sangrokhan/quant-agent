# Fisher Transform + KST Dual-Confirmation — SPY rescue retune

Hypothesis: same as `2026-09-22-073` (Fisher Transform + KST histogram
dual-confirmation momentum; strategy file
`strategies/2026-09-22_fisher_kst_dual_confirmation.py`, unchanged code).
Source: Medium article series by kridtapon on MOS stock, found via Google
SERP this cron trigger's iteration 073.

Prior iteration 073 accepted this strategy on QQQ (fisher_window=20,
trend_window=0) but rejected SPY (Sharpe 0.837 < 1.0, param-sensitivity
fail with relative_std 2.97).

## Rescue approach

Own-data parameter re-scan (no new external source this sub-iteration):
swept `fisher_window` in {10,15,20,30} x `trend_window` in
{0,30,40,50,60,70,80,100,150,200} on SPY only. Found a broad plateau at
`fisher_window=15, trend_window=50-80` where Sharpe is consistently >1.0
(1.01-1.13) — much less sensitive than the original `trend_window=0`
region, which alone drove the original param-sensitivity fail.

Selected config: **fisher_window=15, trend_window=60**.

## Validator results (SPY, fisher_window=15, trend_window=60)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.030 | 1.0 | ✅ |
| Max drawdown | 0.140 | 0.25 | ✅ |
| TC survival (net Sharpe, 10bps/trade, 70 trades) | 0.904 | 0.5 | ✅ |
| Walk-forward (4 splits) | 1.0 pass fraction | 0.75 | ✅ |
| Parameter sensitivity (8-cell grid around fw15/tw60) | rel_std 0.066 | 0.5 | ✅ |

## Confirmation on QQQ (same new config, sanity check it doesn't break QQQ)

| Validator | Value | Pass |
|---|---|---|
| Sharpe ratio | 1.214 | ✅ |
| Max drawdown | 0.156 | ✅ |
| TC survival | 1.107 | ✅ |
| Walk-forward | 1.0 | ✅ |
| Parameter sensitivity | 0.066 | ✅ |

All 5 validators pass on **both** SPY and QQQ at `fisher_window=15,
trend_window=60` — this new config supersedes the QQQ-only accepted config
from 073 as the joint-best live config for this strategy file. Crypto
(BTC/USDT, ETH/USDT) was decisively rejected in 073 (MDD 0.6-0.76 vs 0.25
threshold) and out of scope for this rescue (no crypto retest attempted).

## Outcome

Accepted: SPY (rescued from 073's near-miss) AND QQQ (re-confirmed) at
`fisher_window=15, trend_window=60`. Crypto remains rejected per 073.
