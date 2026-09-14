# NVI Continuous Sizing Dial — Crypto Leverage-Cap Recalibration (leverage_cap=0.3)

**Strategy file:** `strategies/2026-09-14_nvi_sizing_sma_trend_crypto_lev.py`
**Predecessor:** `2026-09-14-131` (`strategies/2026-09-14_nvi_sizing_sma_trend.py`)

## Hypothesis

2026-09-14-131 (NVI short-horizon ROC z-score continuous sizing dial on an
SMA(trend_window) trend gate) accepted decisively on equity (QQQ+SPY, all 5
validators) but was a narrow MDD near-miss on crypto: BTC/USDT MDD 0.277 and
ETH/USDT MDD 0.270, both just above the 0.25 threshold, at swept
leverage_cap in {1.0, 0.4}. This iteration lowers `leverage_cap` to 0.3 and
scales `base_exposure`/`sensitivity` down proportionally (0.25/0.2-0.3),
following the repo's established leverage-cap-recalibration pattern
(2026-09-14-124/125, -180/181, -182/183). Source/formula unchanged from
2026-09-14-131 (Google AI overview via `browser_exec`,
`https://www.google.com/search?q=Negative+Volume+Index+NVI+formula+construction`)
— no new fetch needed for this recalibration sub-step.

## Grid test (`validation/grid_test.py::run_strategy_grid`)

`param_grid={"leverage_cap":[0.25,0.3,0.35],"sensitivity":[0.2,0.25,0.3],"deadband":[0.2,0.3]}`,
`symbols={"equity":["QQQ","SPY"],"crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`.

- **Overall pass_fraction: 0.435 (94/216)**
- by_asset_class: equity 47/108 (0.435), crypto 47/108 (0.435) — identical
  pass rate across asset classes this time.
- by_vol_regime: low 42/72 (0.583), mid 47/72 (0.653), high 5/72 (0.069) —
  strongly regime-dependent, as with most of this trigger's dials.
- best_cell: crypto ETH/USDT, leverage_cap=0.35/sensitivity=0.2/deadband=0.2,
  mid-vol, Sharpe 2.25.
- worst_cell: equity QQQ, leverage_cap=0.35/sensitivity=0.25/deadband=0.3,
  high-vol, Sharpe -0.05.

## Single-config validators (best config: `leverage_cap=0.3, sensitivity=0.2, deadband=0.2, base_exposure=0.25`)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity (rel-std) | All pass |
|---|---|---|---|---|---|---|
| QQQ | 1.063 (pass) | 0.070 (pass) | 0.264 (**fail**, <0.5) | 0.75 (pass) | 0.537 (**fail**, >0.5) | No |
| SPY | 1.130 (pass) | 0.039 (pass) | 0.229 (**fail**, <0.5) | 1.00 (pass) | 0.537 (**fail**, >0.5) | No |
| BTC/USDT | 1.376 (pass) | 0.204 (pass, fixed from 0.277) | 1.035 (pass) | 1.00 (pass) | 0.433 (pass) | **Yes** |
| ETH/USDT | 1.025 (pass) | 0.177 (pass, fixed from 0.270) | 0.834 (pass) | 1.00 (pass) | 0.585 (**fail**, >0.5) | No |

## Outcome

**Partial accept: BTC/USDT only, all 5 validators pass.**

- Crypto MDD near-miss from 2026-09-14-131 is fully fixed (BTC 0.204,
  ETH 0.177, both comfortably under 0.25) — the leverage-cap-recalibration
  hypothesis mechanism worked as intended.
- ETH/USDT flips to a new failure mode: parameter sensitivity (0.585 vs 0.5
  threshold) — the lower leverage_cap/sensitivity range compresses Sharpe
  variation less evenly across ETH's param sweep than BTC's.
- QQQ/SPY, which were fully accepted at the *original* (higher
  leverage_cap=1.0/0.6) config in 2026-09-14-131, now FAIL at this
  crypto-recalibrated config on transaction-cost-survival (net Sharpe
  0.26-0.23 < 0.5) and parameter sensitivity (0.537 > 0.5) — the tighter
  leverage_cap=0.3 ceiling isn't right for equity, confirming crypto and
  equity need genuinely separate leverage_cap defaults for this dial
  (equity should keep 2026-09-14-131's original defaults, not this
  recalibrated one).

Net repo state for NVI continuous-sizing dial: equity QQQ+SPY accepted at
2026-09-14-131's original config (leverage_cap up to 1.0/0.6); crypto
BTC/USDT accepted at this entry's leverage_cap=0.3 config; crypto ETH/USDT
still not accepted under either config (MDD near-miss under the original,
param-sensitivity fail under this one) — flagged as a genuine near-miss for
a future ETH-specific tune (e.g. leverage_cap=0.3 but with sensitivity fixed
narrower, e.g. [0.15,0.2,0.25] instead of [0.2,0.25,0.3], to tighten the
param-sensitivity grid range).
