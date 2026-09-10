# Backtest report: KRE (Regional Banks) SMA trend-following gated by
# TLT/IEF yield-curve-steepening proxy

**Strategy file:** `strategies/2026-09-11_kre_tlt_ief_steepening_gate.py`
**Hypothesis source:** https://marketwise.com/investing/investing-yield-curve-steepening-2026-what-it-means-stocks-banks-bonds/
(regional bank NIM sensitivity to curve steepening), repurposing this repo's
already-validated TLT/IEF duration-ratio construction
(`strategies/2026-09-11_tlt_ief_ratio_regime_gate.py`, id 2026-09-11-045) in
the opposite ("steepening", ratio-down) direction.

## Hypothesis

Regional bank stocks (KRE) benefit from net-interest-margin widening during
yield-curve steepening. Proxy steepening via the TLT/IEF price ratio: when
TLT (20+yr) underperforms IEF (7-10yr) -- ratio below its own SMA -- long
yields are hypothesized to be rising faster than intermediate yields
(back-end steepening), a favorable NIM regime. Gate a standard SMA
trend-following signal on KRE (and QQQ/SPY as cross-checks) by this regime.

## Grid test summary (Step 6)

`param_grid={"trend_sma_window": [30,50,100], "ratio_sma_window": [30,50,100]}`,
`symbols={"equity": ["KRE","QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 135 total cells, 2018-01-01 to 2026-09-01.

- **pass_fraction: 0.185 (25/135)**
- by_asset_class: equity 25/81, crypto 0/54 (decisive -- no yield-curve
  analog for crypto, expected)
- by_vol_regime: low 18/45, mid 7/45, high 0/45
- best_cell: SPY, trend_sma_window=50/ratio_sma_window=30, low-vol regime,
  Sharpe=2.357
- **KRE itself (the originally-hypothesized target): 0/27 cells passed.**
  Full-sample KRE Sharpe never exceeded 0.437 across the entire 7x7 extended
  parameter sweep (trend in {20,30,50,75,100,150,200} x ratio in same set x
  invert_signal in {False,True}) -- see below.

## Single-config validation (Step 7)

Full-sample (2018-01-01 to 2026-09-01) Sharpe / max drawdown, best grid
configs per symbol:

| Symbol | trend_sma_window | ratio_sma_window | Sharpe | MDD |
|---|---|---|---|---|
| KRE | 30 | 50 | 0.437 | 0.389 |
| KRE | 50 | 50 | 0.261 | 0.377 |
| KRE | 100 | 50 | 0.076 | 0.467 |
| QQQ | 100 | 50 | 0.708 | 0.285 |
| SPY | 100 | 50 | 0.798 | 0.222 |

An extended local parameter search on KRE alone (trend_sma_window in
{20,30,50,75,100,150,200} x ratio_sma_window in same set x
invert_signal in {False,True}, 98 combos) found **no configuration with
Sharpe > 0.9** -- the steepening-proxy gate does not rescue KRE's raw trend
signal at all; KRE's own SMA trend-following (ungated) has historically been
noisy/high-drawdown (2023 regional-bank crisis drawdown alone breaches the
0.25 MDD budget on most configs).

- `check_sharpe_ratio`: **FAILED** for KRE (all configs, best 0.437 < 1.0
  threshold); FAILED for QQQ (0.708) and SPY (0.798) full-sample too, though
  both showed a strong best-cell (low-vol tercile) Sharpe > 2 in the grid --
  the edge, if any, is concentrated narrowly in one vol regime and does not
  hold full-sample.
- `check_max_drawdown`: FAILED for KRE (0.389-0.467 vs 0.25 budget, driven
  by the 2023 regional-bank-crisis drawdown which the gate does not avoid).
  QQQ/SPY MDD (0.222-0.285) marginal/near-budget.
- Walk-forward / parameter-sensitivity: not run given the decisive KRE full-
  sample Sharpe/MDD failure (workload=max, but no value in running the full
  suite on a config already failing the two cheapest/most fundamental gates).

## Decision: REJECTED

KRE (the originally-hypothesized target) fails decisively on both Sharpe and
max-drawdown across the full parameter space tested. QQQ/SPY show only a
narrow low-vol-tercile edge (consistent with several other TLT/IEF-ratio-
based near-misses already in this knowledge base, e.g. 2026-09-11-045/046),
not a full-sample edge, so this specific "steepening" (ratio-down) direction
does not clear the bar the way the "flight-to-duration" (ratio-up) direction
did for QQQ. The 2023 regional-bank crisis (SVB/Signature/First Republic)
appears to be the dominant driver of KRE's drawdown that this macro proxy
gate does not filter out (a single-name banking-crisis contagion event is
not the same risk factor as a smooth curve-steepening regime).

## Notes for future loops

- The TLT/IEF ratio construction (2026-09-11-045) works for QQQ in the
  "flight-to-duration" (ratio-up) direction but not for KRE in the
  "steepening" (ratio-down) direction -- the mechanism is directionally
  asymmetric, not simply invertible.
- KRE's dominant historical drawdown driver (2023 regional-bank crisis) is
  an idiosyncratic credit-event risk that a smooth trend/ratio-based macro
  gate cannot filter; a future loop revisiting KRE might need an explicit
  credit-stress circuit-breaker (e.g. HYG/LQD spread or KRE's own realized-
  vol spike) rather than a rates-regime proxy.
