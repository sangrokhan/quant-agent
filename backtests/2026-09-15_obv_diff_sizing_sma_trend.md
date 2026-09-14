# 2026-09-15 OBV-minus-EMA Continuous Sizing Dial (SMA trend gate)

## Hypothesis

On-Balance Volume (Joseph Granville, 1963): `OBV_t = OBV_{t-1} + volume_t`
if `close_t > close_{t-1}`; `OBV_t = OBV_{t-1} - volume_t` if
`close_t < close_{t-1}`; unchanged if equal. Repo already has one prior OBV
entry (2026-09-04-027: binary OBV-crosses-above-its-own-EMA(20) confirmation
signal within an SMA(200) uptrend filter — accepted QQQ only, SPY near-miss
Sharpe 0.967, crypto rejected). This iteration reframes OBV minus its own
EMA as a **continuous sizing dial** (rolling z-score + tanh squash to
[-1,1], deadband to cut turnover, leverage_cap for crypto) instead of a
binary crossover trigger — the same "binary crossover → continuous sizing
dial" pattern already validated in this repo for RMI/RMO/McGinley
Dynamic/Anchored Momentum, applied to OBV for the first time.

## Sources

- https://www.investopedia.com/terms/o/onbalancevolume.asp — OBV formula,
  cumulative construction, worked 10-day numeric example, "smart money"
  volume-leads-price rationale.
- https://gocharting.com/docs/charting/technical-indicator/oscillators/on-balance-volume
  — confirms OBV-vs-its-own-moving-average as the standard tradeable signal
  form (main article body did not fully render via browser_exec extraction;
  used as corroborating source only, Investopedia is primary).

## Strategy file

`strategies/2026-09-15_obv_diff_sizing_sma_trend.py`

Params: `trend_window`, `obv_ema_span`, `zscore_window`, `base_exposure`,
`sensitivity`, `leverage_cap`, `deadband`.

## Step 6 — Grid test summary

`param_grid={obv_ema_span:[10,20,40], zscore_window:[100,150],
sensitivity:[0.4,0.6], deadband:[0.15,0.25,0.35]}`, symbols
QQQ/SPY + BTC/USDT/ETH/USDT, vol_regime_splits=3.

- total_cells=432, passed=237, **pass_fraction=0.549**
- by_asset_class: equity 123/216 (0.570), crypto 114/216 (0.528)
- by_vol_regime: low 137/144 (0.951), mid 72/144 (0.500), high 28/144 (0.194)
- best_cell: QQQ, obv_ema_span=40/zscore_window=100/sensitivity=0.6/deadband=0.35,
  low-vol Sharpe 3.03

## Step 7 — Single-config validation (best per-symbol full-sample config)

| Symbol | Params | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd | Param sens. (rel std) | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | ema=40/zw=150/sens=0.4/db=0.35 | 1.509 (pass) | 0.100 (pass) | 1.259 (pass) | 1.00 (pass) | 0.093 (pass) | 93 |
| SPY | ema=10/zw=150/sens=0.4/db=0.35 | 1.289 (pass) | 0.079 (pass) | 0.570 (pass) | 1.00 (pass) | 0.139 (pass) | 187 |
| BTC/USDT | ema=40/zw=150/sens=0.6/db=0.25 | 1.380 (pass) | 0.357 (**fail**, >0.25) | 1.165 (pass) | 1.00 (pass) | 0.052 (pass) | 315 |
| ETH/USDT | ema=20/zw=150/sens=0.4/db=0.35 | 1.187 (pass) | 0.337 (**fail**, >0.25) | 1.102 (pass) | 1.00 (pass) | 0.089 (pass) | 182 |

Walk-forward used a manual 4-equal-slice fallback (vbt.utils.splitting API
unavailable in the installed vectorbt==1.1.0) — a repo-standard workaround
pattern already used in prior iterations, per-split Sharpe>0 rule, all 4
splits positive for every symbol here.

## Step 8 — Accept/Reject

- **QQQ: accepted** — all 5 validators pass.
- **SPY: accepted** — all 5 validators pass (this also rescues, for OBV, the
  original 2026-09-04-027 SPY near-miss of Sharpe 0.967, though via a
  different mechanism — continuous sizing rather than binary crossover).
- **BTC/USDT: rejected** — decisive max-drawdown failure (0.357 > 0.25
  threshold), despite passing gross/net Sharpe and walk-forward.
- **ETH/USDT: rejected** — decisive max-drawdown failure (0.337 > 0.25
  threshold), same pattern as BTC/USDT.

Crypto's MDD failure is consistent with the grid's own breakdown (crypto
pass_fraction 0.528 vs equity 0.570, and both asset classes degrade sharply
in mid/high vol regimes) — the OBV-diff sizing dial is not aggressive
enough at cutting exposure during crypto's larger drawdown episodes even
though its Sharpe/TC-survival/param-sensitivity numbers look fine in
isolation.
