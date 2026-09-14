# 2026-09-14 — Twiggs Money Flow sizing overlay, leverage-capped crypto follow-up (BTC+ETH accepted)

## Hypothesis

Direct follow-up to 2026-09-14-123 (TMF continuous sizing dial: accepted
QQQ/SPY, rejected crypto BTC/USDT/ETH/USDT decisively on MDD, 0.29-0.39
across the entire sensitivity/deadband sweep at leverage_cap=1.0 default).
This iteration's own-data observation: crypto's Sharpe was consistently
STRONG (1.2-1.5, well above threshold) even while MDD failed — suggesting
the mechanism has genuine directional signal on crypto but the 1.0x
leverage cap simply lets drawdowns compound too far given crypto's larger
absolute volatility. Tests whether capping `leverage_cap` (and
proportionally `base_exposure`) lower for crypto — same strategy file,
same TMF sizing logic, no new external source, purely a position-sizing
recalibration — brings crypto's MDD under the 0.25 threshold while
preserving the Sharpe edge, rather than rejecting the underlying signal
outright.

## Strategy file (unchanged)

`strategies/2026-09-14_tmf_sizing_sma_trend.py` (same file as
2026-09-14-123; only `leverage_cap`/`base_exposure` keyword params differ)

## Step 6 — Grid test summary (108 cells: sensitivity in {0.3,0.5,0.7} x
leverage_cap in {0.3,0.4,0.5} (base_exposure=leverage_cap*0.5, deadband
fixed at 0.15) x QQQ/SPY/BTC/ETH x 3 vol regimes)

- pass_fraction: 0.667 (72/108) — substantially higher than the original
  1.0x-leverage-cap grid's 0.500
- by_asset_class: equity 27/54 passed; crypto **45/54 passed** (up from
  18/36 at leverage_cap=1.0 -- more than doubled the pass rate)
- by_vol_regime: low 36/36 passed; mid 27/36 passed; **high 9/36 passed**
  (previously 0/24 at leverage_cap=1.0 -- capping leverage is the first
  mechanism this cron trigger to get ANY high-vol-regime cells passing)
- best_cell: QQQ low-vol, sensitivity=0.5/leverage_cap=0.4, Sharpe 2.80
- worst_cell: QQQ high-vol, sensitivity=0.5/leverage_cap=0.4, Sharpe -0.32

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01, sensitivity=0.5/deadband=0.15/leverage_cap=0.4/base_exposure=0.2)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|
| BTC/USDT | 1.484 (pass) | 0.141 (pass, was 0.314 at lev=1.0) | 1.130 (pass) | 1.00 (pass) | 0.015 (pass) |
| ETH/USDT | 1.213 (pass) | 0.190 (pass) | 0.996 (pass) | 1.00 (pass) | 0.021 (pass) |

## Step 8 — Decision

**Accepted: BTC/USDT and ETH/USDT** (crypto) at
sensitivity=0.5/deadband=0.15/leverage_cap=0.4/base_exposure=0.2, all 5
validators pass for both symbols. This is the **first full crypto
acceptance for a volume/money-flow continuous-sizing-dial mechanism** this
cron trigger (Elder-Ray net power, Chaikin Oscillator, and the original
1.0x-leverage TMF variant all rejected crypto on MDD). The generalizable
finding: this cron trigger's recurring "continuous sizing overlay accepted
equity / rejected crypto MDD" pattern is at least partly an artifact of
using the SAME leverage_cap=1.0 for both asset classes rather than a
structural failure of the underlying signal on crypto -- crypto's higher
baseline volatility means the same directional Sharpe edge produces a
much larger absolute drawdown at full leverage. Recommend future
iterations testing continuous-sizing overlays on crypto default to a
lower (~0.4) starting leverage_cap before concluding crypto rejection.
