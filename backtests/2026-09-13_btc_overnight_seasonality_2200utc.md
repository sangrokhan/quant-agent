# 2026-09-13: BTC "Overnight Seasonality" 22:00 UTC hourly window

**Hypothesis (id 2026-09-13-002):** Per Quantpedia's "Overnight Seasonality
in Bitcoin" (https://quantpedia.com/strategies/intraday-seasonality-in-bitcoin,
citing Padysak & Vojtko SSRN 4081000): BTC's 22:00-23:00 UTC hour is the
one window when every major traditional exchange (NYSE, Tokyo, Hong Kong,
India, Australia, London) is simultaneously closed; the source's own
mechanical rule is "open a long position in BTC at 22:00 (UTC+0) and hold
it for two hours." Source's own reported 2015-2021 Gemini-exchange sample:
33% annualized return, Sharpe 1.58, MDD -34.04%.

First hourly-bar, hour-of-day seasonality strategy tested in this repo
(prior seasonality entries all used daily bars: day-of-week, turn-of-month,
weekend-effect families).

## Grid test (Step 6)

`run_strategy_grid`, params `entry_hour in [21,22,23]`, `hold_hours in
[1,2,3]`, symbols equity=[QQQ] (feasibility-control, daily bars ->
always-flat by construction) crypto=[BTC/USDT, ETH/USDT] (native 1h bars),
vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.0 (0/81 cells)** -- decisive fail.
- by_asset_class: equity 0/27 (expected -- not applicable to daily bars,
  confirms feasibility-control worked as designed), crypto 0/54.
- by_vol_regime: low 0/27, mid 0/27, high 0/27.
- best_cell: crypto/BTC-USDT/high-vol, entry_hour=21/hold_hours=2, Sharpe
  0.461 (still well below 1.0 threshold; note grid's Sharpe helper uses
  this repo's default 252-periods/year annualization rather than an
  hourly-correct 252*24 factor -- re-checked with the correct hourly
  annualization on the source's exact 22:00/2h config below).

## Single-config check (source's exact config: entry_hour=22, hold_hours=2, BTC/USDT, full sample, hourly-correct annualization)

- Active bars: 5,600 of 67,141 hourly bars (2019-01-01 to 2026-09-01)
- Sharpe (periods_per_year=252*24=6048): **0.037** (threshold 1.0) -- FAIL,
  decisively far from the source's own claimed 1.58
- Max drawdown: **0.424** (threshold 0.25) -- FAIL

## Outcome: REJECTED (decisive)

The source's own reported edge (2015-2021 Gemini sample) does not
replicate on this repo's 2019-2026 Binance BTC/USDT hourly sample: Sharpe
collapses from a claimed 1.58 to 0.037, and drawdown nearly doubles the
25% threshold. Plausible explanations (noted for future reference, not
independently confirmed here): (a) the effect may have been exchange- or
era-specific (Gemini vs Binance, and pre- vs post-2021 crypto
market-structure/24h-liquidity changes eroded the "only BTC is tradeable"
rationale as more venues/derivatives matured), (b) the source's own sample
predates the 2021+ maturation of crypto derivatives/perpetuals that
arguably reduced the liquidity-vacuum effect the strategy relies on. No
transaction-cost/walk-forward/parameter-sensitivity validators run -- grid
pass_fraction 0.0 across all three tested entry-hour/hold-length
neighbors of the source's own exact config is decisive.

Source URL: https://quantpedia.com/strategies/intraday-seasonality-in-bitcoin
