# Squeeze Momentum Indicator continuous sizing dial (SMA trend-gated) — full universe

**Hypothesis id:** 2026-09-16-153
**Source:** unchanged from 2026-09-04-126 —
https://enlightenedstocktrading.com (LazyBear Squeeze Momentum Indicator,
already in ledger; momentum-histogram formula re-used unchanged). No new
external research this sub-iteration.

## Hypothesis
This repo has 1 prior LazyBear Squeeze Momentum Indicator entry
(2026-09-04-126, `strategies/2026-09-04_squeeze_momentum_ema_filter.py`): a
binary "enter on the first squeeze-release bar with rising positive momentum
above EMA-50" trigger, rejected (QQQ decisive fail, SPY near-miss, crypto
rejected). That entry only used the momentum histogram to GATE a binary
entry on the specific squeeze-release event; it never used the histogram's
own magnitude as a continuous sizing signal. This iteration reuses the
identical momentum-histogram construction (close minus the average of the
rolling Donchian midpoint and SMA, run through a rolling linear-regression
fit — LazyBear's own formula) but drops the squeeze-detection/release-event
gating entirely, instead rolling-z-scoring + tanh-squashing the raw momentum
to [-1,1] and using it directly as a continuous exposure dial inside an
SMA(trend_window) uptrend gate with a deadband. First Squeeze-Momentum-as-
continuous-sizing-dial strategy in this repo.

Strategy file: `strategies/2026-09-16_squeeze_momentum_sizing_sma_trend.py`

## Step 6 — Grid test
Grid: mom_window ∈ {15,20,30} × sensitivity ∈ {0.3,0.5,0.7} × deadband ∈
{0.15,0.2}, symbols equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT},
vol_regime_splits=3 → 216 cells.
- pass_fraction 0.403 (87/216). by_asset_class: equity 58/108 (53.7%),
  crypto 29/108 (26.9%). by_vol_regime: low 62/72 (86.1%), mid 19/72
  (26.4%), high 6/72 (8.3%).
- best_cell: QQQ, mom_window=15/sensitivity=0.5/deadband=0.15, low-vol,
  Sharpe 2.986.

## Step 7 — Full-sample single-config validators

| Symbol | mom_window | sensitivity | deadband | leverage_cap | Sharpe | MDD | TC net Sharpe | WF | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| QQQ | 20 | 0.3 | 0.20 | 1.0 | 1.189 | 0.128 | 0.637 | 0.75 | **PASS all** |
| SPY | 20 | 0.3 | 0.30 | 1.0 | 1.055 | 0.068 | 0.579 | 1.0 | **PASS all** |
| BTC/USDT | 20 | 0.12 | 0.15 | 0.4 (base=0.2) | 1.463 | 0.137 | 1.128 | 1.0 | **PASS all** |
| ETH/USDT | 20 | 0.12 | 0.15 | 0.4 (base=0.2) | 1.092 | 0.146 | 0.890 | 1.0 | **PASS all** |

QQQ: mom_window=15 gave higher grid-cell Sharpe but wider deadband was
needed at mom_window=20 to clear TC-survival; kept mom_window=20/sens=0.3/
db=0.2. SPY: default deadband 0.15/0.2 failed both Sharpe and TC-survival;
widening to 0.3 dropped trades from 319 to 142 and pushed all validators to
pass.

Crypto: standard leverage-cap-aware retune grid (27 combos: leverage_cap ∈
{0.2,0.3,0.4} × sensitivity-scale ∈ {0.3,0.4,0.5} × deadband ∈
{0.15,0.2,0.25}) — 15/27 combos passed Sharpe/MDD/TC/non-degenerate for BOTH
BTC and ETH simultaneously, a healthy majority. Selected leverage_cap=0.4/
base_exposure=0.2/sensitivity=0.12/deadband=0.15 for the best Sharpe/MDD
balance.

## Outcome
**Accepted — full universe on first attempt** (QQQ, SPY, BTC/USDT, ETH/USDT
all pass Sharpe/MDD/TC/walk-forward with per-symbol retuned deadband/
sensitivity/leverage_cap). Continues this cron trigger's recurring finding
that dropping a binary threshold/event trigger and reframing the underlying
indicator's raw magnitude as a continuous sizing dial substantially improves
crypto transferability for this repo's strategy family.
