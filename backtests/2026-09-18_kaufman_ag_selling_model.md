# Kaufman Ag Selling Model — grain ETF short-seasonal (2026-09-18)

## Hypothesis

Perry J. Kaufman's "Ag Selling Model" (TASC August 2026, "An Ag Selling
Model") is a seasonal timing model for producers to hedge/sell grain
positions: short entry when price rallies high enough above its own trend
(40-day SMA + 20-day ATR x 2.5 buffer) during the "selling season" (starting
`delay_in_months` after the crop-year start month), rate-limited to one
sell every `days_between_sales` trading days; flatten (cover) at the start
of the next crop year.

Adapted here as a short-only strategy on grain-tracking ETFs (CORN, WEAT,
SOYB) as a proxy for the futures contracts in the original article (this
repo's `data/loaders.py` doesn't support futures contracts directly).

Source: https://traders.com/Documentation/FEEDbk_docs/2026/08/TradersTips.html
(thinkorswim thinkscript, fully disclosed; fetched via browser_exec --
web_search DDGS backend failing this cron trigger throughout).

## Grid test

`atr_factor in {2.0,2.5,3.0} x days_between_sales in {20,30,45}`, equity
only (CORN, WEAT, SOYB -- no crypto analog exists for a grain-commodity
seasonal model), vol_regime_splits=3, 2018-01-01..2026-09-01:

- total_cells=81, passed_cells=0, **pass_fraction=0.0** -- decisive
  rejection across every parameter combination, symbol, and vol regime.
- best_cell: atr_factor=2.5/days_between_sales=20, SOYB mid-vol, Sharpe
  only 0.658 (still below 1.0 threshold even at its single best tercile).

## Single-config validation (atr_factor=2.5, days_between_sales=20)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe, 10bps) |
|---|---|---|---|
| CORN | -0.076 (fail) | 0.459 (fail) | -0.091 (fail) |
| WEAT | -0.129 (fail) | 0.557 (fail) | -0.140 (fail) |
| SOYB | -0.125 (fail) | 0.341 (fail) | -0.143 (fail) |

All three ETFs produce net-negative Sharpe over the full sample -- the
short-only seasonal model loses money on average against these ETF proxies
over 2018-2026 (all three grain ETFs were roughly flat-to-down over this
period with high volatility, so a persistent short bias with no
counter-trend filter underperforms decisively).

## Verdict: REJECTED (decisive, all symbols, all grid cells)

This is a clean/uncontroversial rejection, not a near-miss: 0/81 grid
cells pass and full-sample Sharpe is negative for all three ETF proxies.
Likely root cause: the model's edge (if any exists in the original futures
context) depends on genuine seasonal producer-hedging supply/demand
dynamics specific to the actual futures contract roll and crop calendar,
which an ETF-proxy substitution doesn't replicate faithfully (ETF proxies
roll differently and don't carry the same basis/carry dynamics). Not worth
a rescue attempt without direct futures data access, which this repo's
loaders don't support -- noting this as a feasibility caveat for any future
revisit.
