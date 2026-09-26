# Backtest Report: VIX Term-Structure + eVRP Tail-Hedge Overlay (2026-09-26)

## Hypothesis
Source: QuantPedia's "Hedging Tail Risk with Robust VIXY Models"
(https://quantpedia.com/hedging-tail-risk-with-robust-vixy-models/,
browser_exec, own-research 29 Sep 2025, itself citing Zarattini/Mele/Aziz).

Portfolio: `(1-vixy_weight)` in SPY always + `vixy_weight` dynamically
allocated to VIXY when a hedge signal fires, else that slice sits in cash.
Hedge signal ("Article Strategy I"): expected volatility risk premium
`eVRP = VIX - realized_vol(SPY, window)` <= 0 AND VIX > VIX3M (term
structure inversion). One-day implementation lag per the source's own
disclosed timing.

The source's OWN naive benchmark (VIX>VXV alone, no eVRP) underperforms
pure buy-and-hold SPY (Sharpe 0.38 vs 0.56) -- flagged explicitly by the
source as insufficient, motivating the eVRP refinement tested here.

## Grid test summary (Step 6)

`realized_vol_window in {10,21,42} x vixy_weight in {0.15,0.20,0.30}`,
QQQ/SPY (equity only -- VIX/VIXY have no crypto analog), `vol_regime_splits=3`,
2012-01-01 to 2026-09-01:

- `pass_fraction = 0.574` (31/54) -- the strongest grid pass fraction of any
  strategy tested this cron trigger
- `by_vol_regime`: low 18/18 (100%), mid 9/18, high 4/18
- `best_cell`: realized_vol_window=10, vixy_weight=0.3, QQQ, low-vol,
  Sharpe 2.930

Full local 9-combo full-sample sweep: QQQ 1.132-1.401 (clears 1.0 at every
single tested combo); SPY 1.010-1.199 (also clears 1.0 at every combo).
Notably robust across the ENTIRE local parameter neighborhood for both
symbols -- consistent with the source's own finding that both eVRP and the
VIX/VIX3M term-structure signal are genuine, not overfit artifacts.

## Single-config validation (Step 7)

Config: `realized_vol_window=10, vixy_weight=0.30` (grid-best QQQ cell,
also strong for SPY).

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.401 (pass) | 1.199 (pass) | >= 1.0 |
| Max drawdown | 0.270 (**fail**, narrowly) | 0.181 (pass) | <= 0.25 |
| TC survival (net Sharpe, 5bps/trade) | 1.371 (pass) | 1.183 (pass) | >= 0.5 |
| Walk-forward (4 splits) | 1.00 (pass) | 1.00 (pass) | >= 0.75 |
| Parameter sensitivity (rel. std, 9-cell grid) | 0.075 (pass) | 0.058 (pass) | <= 0.5 |

SPY passes ALL 5 validators cleanly. QQQ fails only max drawdown, narrowly
(0.270 vs 0.25 -- a 2 percentage point miss), with all other validators
passing comfortably including an extremely low parameter-sensitivity
relative std (0.075) -- one of the most robust configs tested this cron
trigger. Pure buy-and-hold QQQ has structurally higher drawdowns than SPY
(tech-heavy, higher beta), so the fixed 30% VIXY hedge weight that works for
SPY doesn't fully offset QQQ's larger crash exposure.

## Decision: ACCEPTED (SPY only); QQQ near-miss (MDD-only, not pursued
further this iteration given time budget -- a future loop could retest QQQ
with a larger vixy_weight, e.g. 0.35-0.40, to close the 2pp MDD gap).

Num trades: SPY 40, QQQ 84 (regime-switch count over 2012-2026, low
turnover, easily survives 5bps/trade transaction costs).

Source: https://quantpedia.com/hedging-tail-risk-with-robust-vixy-models/
(browser_exec, own-research, free).
