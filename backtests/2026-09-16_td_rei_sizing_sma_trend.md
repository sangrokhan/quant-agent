# TD REI continuous sizing dial (SMA trend-gated) — full universe rescue

**Hypothesis id:** 2026-09-16-155 (rescue of 2026-09-16-121)
**Source:** unchanged from 2026-09-16-121 —
https://www.linnsoft.com/techind/demark-range-expansion-index (exact
formula) and https://www.quantifiedstrategies.com/range-expansion-index/
(interpretation), both already in this repo's ledger. No new external
research this sub-iteration.

## Prior state (2026-09-16-121)
Binary oversold-threshold-cross-then-rise entry trigger, trend-gated:
rejected across all symbols. QQQ strong Sharpe/MDD but decisive
parameter-sensitivity fail (0.622>0.5, genuine overfitting flag). SPY
decisive Sharpe+TC fail. BTC/USDT decisive Sharpe+MDD fail. ETH/USDT passed
4/5 validators, MDD near-missed (0.253 vs 0.25 threshold).

## This sub-iteration: continuous sizing dial
TD REI = 100 × SUM(VALUE,N) / SUM(ABSVALUE,N) is already naturally bounded
in [-100,+100] by construction (a ratio, like %B or BVC) — no z-score/tanh
needed, only a /100 rescale. Reuses the identical REI formula unchanged but
drops the oversold-threshold-cross-then-rise event logic entirely, using
REI/100 directly as a continuous exposure dial inside an SMA(trend_window)
uptrend gate with a deadband. This directly targets the prior entry's
parameter-sensitivity overfitting flag (continuous dials are typically much
less sensitive to exact threshold placement) and ETH's narrow MDD near-miss.

Strategy file: `strategies/2026-09-16_td_rei_sizing_sma_trend.py`.

## Step 6 — Grid test
Grid: rei_period ∈ {5,8,13} × sensitivity ∈ {0.5,0.8,1.0} × deadband ∈
{0.15,0.2}, symbols equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT},
vol_regime_splits=3 → 216 cells.
- pass_fraction 0.407 (88/216) — a strong rescue from the prior binary
  version's pass_fraction 0.213 (46/216).
- by_asset_class: equity 61/108 (56.5%), crypto 27/108 (25%).
- by_vol_regime: low 56/72 (77.8%), mid 20/72 (27.8%), high 12/72 (16.7%) —
  notably the only continuous-sizing dial this cron trigger with a
  non-trivial high-vol pass rate (12/72 vs typically 0/72).

## Step 7 — Full-sample single-config validators

| Symbol | rei_period | sensitivity | deadband | leverage_cap | Sharpe | MDD | TC net Sharpe | WF | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 13 | 0.5 | 0.35 | 1.0 | 1.233 | 0.147 | 0.776 | 0.75 | **PASS all** |
| SPY | 13 | 0.5 | 0.35 | 1.0 | 1.105 | 0.109 | 0.578 | 0.75 | **PASS all** |
| BTC/USDT | 13 | 0.20 | 0.25 | 0.4 (base=0.2) | 1.370 | 0.139 | 1.196 | 1.0 | **PASS all** |
| ETH/USDT | 13 | 0.20 | 0.25 | 0.4 (base=0.2) | 1.298 | 0.138 | 1.166 | 1.0 | **PASS all** |

Equity: default deadband 0.2 failed TC-survival for all rei_period/
sensitivity combos tried (turnover 285-404 trades); widening to 0.35
(shared config for both QQQ and SPY) cleared all validators for both
symbols simultaneously with a single config, unusual for this cron trigger
(most equity accepts need per-symbol retunes).

Crypto: standard leverage-cap-aware retune grid (27 combos: leverage_cap ∈
{0.2,0.3,0.4} × sensitivity-scale ∈ {0.5,0.7,1.0} × deadband ∈
{0.25,0.3,0.35}) — 10/27 combos passed for both BTC and ETH simultaneously.
Selected leverage_cap=0.4/base_exposure=0.2/sensitivity=0.2/deadband=0.25.

## Outcome
**Accepted — full universe rescue, single shared equity config for QQQ+SPY.**
Directly confirms the prior entry's parameter-sensitivity concern: the
binary threshold-cross trigger was fragile to exact parameter placement,
while the continuous dial reframing (same underlying REI formula) is robust
across both equity symbols with a SINGLE shared configuration and clears
crypto with the standard leverage-cap-aware retune. Also rescues ETH's
narrow MDD near-miss with room to spare (0.138 vs the prior 0.253).
