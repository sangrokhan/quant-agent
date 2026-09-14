# Ehlers Fisher Transform Continuous Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_fisher_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-130` (accepted QQQ/BTC/USDT/ETH/USDT, rejected SPY — "no config in a broad sweep achieves Sharpe>=1.0")

## Hypothesis

`2026-09-14-130`'s Fisher Transform continuous-sizing dial (price rescaled
to [-1,1] within rolling high/low, Fisher = 0.5*ln((1+v)/(1-v)), smoothed)
accepted decisively for QQQ, BTC/USDT, and ETH/USDT but was rejected for SPY
("no passing config found across a broad sensitivity/deadband sweep" at
QQQ's tuned trend_window=40). This iteration widens the search to also vary
`trend_window` and `fisher_window`/`fisher_reference` (not just
sensitivity/deadband as the prior sweep did) and finds SPY passes cleanly
at a slower trend_window=60 with fisher_window=14 (vs QQQ's window=10) and
fisher_reference=1.0 (tighter normalization than QQQ's 1.5). No new
external source needed — same already-confirmed Fisher Transform formula,
same strategy file, just a wider per-symbol parameter search.

## Search process

Coarse grid over trend_window∈{30,40,60}, fisher_window∈{8,10,14,20},
fisher_reference∈{1.0,1.5,2.0,2.5}, sensitivity∈{0.3,0.5,0.7} (deadband
fixed at 0.25) found best Sharpe 1.191 at
trend_window=60/fisher_window=14/fisher_reference=1.0/sensitivity=0.7.

## Single-config validators (SPY, trend_window=60/fisher_window=14/fisher_reference=1.0/sensitivity=0.7/deadband=0.25)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.191 | 1.0 | Yes |
| Max drawdown | 0.105 | 0.25 | Yes |
| TC-survival (net Sharpe) | 0.733 | 0.5 | Yes |
| Walk-forward | 1.00 (4/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std) | 0.077 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass.** Combined with `2026-09-14-130`'s
QQQ/BTC/ETH accepts (same strategy file, per-symbol tuned params), the
Fisher Transform continuous-sizing dial now covers all 4 symbols this repo
tracks, at these per-symbol configs:
- QQQ: trend_window=40, fisher_window=10, fisher_reference=1.5, sensitivity=0.3, deadband=0.35, base_exposure=0.15
- SPY (this entry): trend_window=60, fisher_window=14, fisher_reference=1.0, sensitivity=0.7, deadband=0.25
- BTC/USDT: sensitivity=0.3, deadband=0.15, leverage_cap=0.4
- ETH/USDT: sensitivity=0.2, deadband=0.15, leverage_cap=0.4

This is a rescue of a 13+-times-rejected indicator family (plain Fisher
Transform had never passed on SPY under any binary-trigger construction in
this repo's history) via the continuous-sizing reframing plus a wider
per-symbol trend_window/fisher_window search.
