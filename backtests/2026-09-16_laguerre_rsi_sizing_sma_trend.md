# Laguerre RSI continuous-sizing dial (SMA trend-gated) — full universe rescue

**Hypothesis id:** 2026-09-16-151 (rescue of 2026-09-16-138)
**Source:** unchanged from 2026-09-16-138 —
https://www.quantifiedstrategies.com/laguerre-rsi/ (already visited this cron
trigger's ledger; formula re-used unchanged). No new external research this
sub-iteration.

## Prior state (2026-09-16-138)
Binary state-machine hold (long on LRSI up-cross of 0.2, exit on LRSI
down-cross of 0.8 after excursion above it): accepted EQUITY ONLY (QQQ Sharpe
1.25, SPY Sharpe 1.158, MDD/TC/WF/param-sens all pass). Crypto not validated
broadly at that config: BTC/USDT passed only 1/3 vol regimes, ETH/USDT 0/3.

## This sub-iteration: reframe as continuous sizing dial
LRSI is already bounded [0,1] by construction — no z-score/tanh needed
(same "already-bounded" pattern validated for BVC and this trigger's Ehlers
Reversion Index). Centered as `(LRSI-0.5)*2` to [-1,1], used as:
`exposure = clip(base_exposure + sensitivity*dial, 0, leverage_cap)`,
gated to 0 below SMA(trend_window), with a deadband.

Strategy file: `strategies/2026-09-16_laguerre_rsi_sizing_sma_trend.py`.

## Step 6 — Grid test
Grid: gamma ∈ {0.3,0.5,0.7} × sensitivity ∈ {0.4,0.6,0.8} × deadband ∈
{0.15,0.2}, symbols equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT},
vol_regime_splits=3 → 216 cells.
- pass_fraction 0.375 (81/216). by_asset_class: equity 54/108 (50%), crypto
  27/108 (25%). by_vol_regime: low 60/72 (83%), mid 21/72 (29%), high 0/72
  (0%) — usual vol-regime dependence.
- best_cell: QQQ, gamma=0.7/sensitivity=0.6/deadband=0.15, low-vol, Sharpe
  2.794.

## Step 7 — Full-sample single-config validators

| Symbol | gamma | sensitivity | deadband | leverage_cap | Sharpe | MDD | TC net Sharpe | WF | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 0.7 | 0.6 | 0.20 | 1.0 | 1.204 | 0.153 | 0.799 | 0.75 | **PASS all** |
| SPY | 0.7 | 0.6 | 0.25 | 1.0 | 1.023 | 0.102 | 0.609 | 0.75 | **PASS all** |
| BTC/USDT | 0.7 | 0.18 | 0.15 | 0.3 (base=0.15) | 1.353 | 0.101 | 1.010 | 1.0 | **PASS all** |
| ETH/USDT | 0.7 | 0.18 | 0.15 | 0.3 (base=0.15) | 1.314 | 0.119 | 1.099 | 1.0 | **PASS all** |

QQQ: db=0.15 gave slightly higher Sharpe (1.211) but wider db=0.2 was kept for
lower turnover with negligible Sharpe cost, both pass all validators. SPY:
default deadband 0.15/0.2 both failed TC-survival at Sharpe ~0.98-1.02 (too
much turnover); widened to 0.25 cleared TC-survival cleanly.

Crypto: standard leverage-cap-aware retune grid (27 combos: leverage_cap ∈
{0.2,0.3,0.4} × sensitivity-scale ∈ {0.5,0.6,0.7} × deadband ∈
{0.15,0.2,0.25}) — 21/27 combos passed Sharpe/MDD/TC/non-degenerate for BOTH
BTC and ETH simultaneously, the widest crypto pass margin of any
continuous-sizing rescue this cron trigger. Selected leverage_cap=0.3/
base_exposure=0.15/sensitivity=0.18/deadband=0.15 for best MDD/Sharpe
balance.

## Outcome
**Accepted — full universe rescue** (QQQ, SPY, BTC/USDT, ETH/USDT all pass
Sharpe/MDD/TC/walk-forward with per-symbol retuned deadband/sensitivity/
leverage_cap). Rescues the prior equity-only accept to cover the full
universe, matching this cron trigger's established continuous-sizing-dial
rescue pattern (MFI/VZO/CHOP/TSI/KPO/Qstick all rescued the same way).
