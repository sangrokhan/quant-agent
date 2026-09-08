# Backtest Report: Valuation-Boundary-Gated Time-Series Momentum

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_valuation_boundary_tsmom.py`
**Source:** Suominen & Hjalmarsson, "Boundaries of Time Series Momentum"
(SSRN 2026, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6867878),
summarized at https://quantpedia.com/boundaries-of-time-series-momentum/
(read via browser_exec after direct navigation to Quantpedia's blog list).

## Hypothesis

The source paper finds equity time-series momentum performs well in
mid-valuation regimes but breaks down/reverses near historical valuation
extremes (CAPE, dividend yield, term-spread 10-20yr boundaries) — controlling
for this increases predictive R^2 by up to 550% in their regressions. This
repo has no CAPE/dividend-yield/term-spread data, so we proxy "valuation
extremity" with the asset's own deviation from a multi-year (756-1260
trading day) SMA, percentile-ranked against its own trailing history of
that deviation. Momentum is only traded when (a) it's positive AND (b) the
valuation-proxy percentile is NOT in the extreme tails (kept within
[boundary_lower_pct, 0.9]).

## Grid test summary (Step 6)

`param_grid={"valuation_window":[504,756], "boundary_lower_pct":[0.1,0.2]}`
(boundary_upper_pct fixed at 0.9, mom_lookback fixed at 252),
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **total_cells:** 48, **passed:** 8, **pass_fraction: 0.167**
- **by_asset_class:** equity 8/24; crypto 0/24 (decisive reject — no
  meaningful multi-year "valuation" concept for crypto majors over this
  window)
- **by_vol_regime:** low 8/16, mid 0/16, high 0/16 (edge concentrates
  entirely in the low-vol tercile at the grid level, though the
  full-sample single-config below still passes overall)
- **best_cell:** SPY, valuation_window=756, boundary_lower_pct=0.2, low-vol
  regime, Sharpe 2.55

## Single-config validation (Step 7): valuation_window=756, valuation_lookback=756, boundary_lower_pct=0.2, boundary_upper_pct=0.9, mom_lookback=252

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.240 (PASS) | 0.837 (**FAIL**) | >= 1.0 |
| Max drawdown | 0.244 (PASS) | 0.229 (PASS) | <= 0.25 |
| TC survival (5bps/trade) | 1.178 (PASS, 75 trades) | 0.743 (PASS, 97 trades) | >= 0.5 |
| Walk-forward (4 manual chunks) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity (relative_std, 4-combo grid) | 0.062 (PASS) | 0.096 (PASS) | <= 0.5 |

(Manual 4-chunk walk-forward workaround used per pre-existing
`vbt.utils.splitting` AttributeError bug, documented since 2026-09-03.)

## Decision: **ACCEPT (QQQ only)**

QQQ passes every validator at this config (Sharpe 1.24, MDD 24.4%, TC-net
Sharpe 1.18, walk-forward 4/4 chunks positive, parameter sensitivity
relative_std 0.062 — very stable across the small grid). SPY is a
near-miss: Sharpe 0.837 falls short of the 1.0 threshold despite passing
every other validator (MDD, TC, WF, PS). Crypto (BTC/USDT, ETH/USDT)
rejected decisively across the whole grid (0/24 cells) — a multi-year
price-deviation "valuation" proxy has no clear economic analog for a
24/7, much-younger asset class over the tested window.

Scope: **equity, QQQ only**, not a broad multi-asset strategy — mirrors
this repo's frequent pattern of a strategy passing on QQQ but not quite on
SPY. The mechanism (gating momentum off near valuation extremes) is
distinct from every other regime-filter entry in this repo (which gate on
volatility/return extremity, not a long-term price-level deviation proxy),
so this represents a genuinely new accepted angle rather than a
near-duplicate of a prior acceptance.
