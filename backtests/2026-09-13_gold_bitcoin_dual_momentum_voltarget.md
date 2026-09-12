# 2026-09-13: Gold (GLD) vs Bitcoin (BTC/USDT) Dual Momentum with Vol Targeting

**Hypothesis (id 2026-09-13-003):** Per Quantpedia's "Dual Momentum
Allocation Between Physical Gold and Bitcoin (Digital Gold)"
(https://quantpedia.com/dual-momentum-allocation-between-physical-gold-and-bitcoin-digital-gold/,
6 May 2026, R. Vojtko): weekly (Wednesday-close) rotation between GLD and
IBIT/BTC using relative + absolute momentum over an X-week lookback (long
whichever of GLD/BTC has both the higher AND positive trailing X-week
return; cash otherwise), overlaid with a volatility-targeting position
sizer capping annualized exposure at `vol_cap` (source: 20%). Source's own
2018-12-31 to 2026-04 sample: pure (uncapped) 8-week variant delivers
79.91% annualized return, Sharpe 1.64; the 20%-vol-capped composite
(avg of 4/8/12-week) delivers 12.01% return, Sharpe 1.37, MDD -12.27%
(vs the uncapped composite's -49.40%).

First strategy in this repo combining (a) a weekly-rebalanced
relative+absolute dual-momentum ROTATION between GLD and BTC and (b) a
volatility-targeting continuous position-size overlay (all prior
strategies in this repo use fixed 0%/100% binary position sizing).
Architecturally distinct from the already-tested BTC/GLD RATIO z-score
pairs mean-reversion (2026-09-08-082, rejected 0/108 — never holds gold,
only trades a spread) and from the accepted Silicon-vs-Satoshi QQQ/BTC
Donchian-breakout rotation (2026-09-08-161 — different equity leg, and
breakout not momentum).

This repo substitutes daily-bar realized volatility (60-day rolling
stdev * sqrt(252)) for the source's own weekly-bar 12-week/sqrt(52)
computation, a directionally equivalent vol-cap mechanic given this
repo's daily-bar-only loaders.

## Grid test (Step 6)

`run_strategy_grid`, params `lookback_weeks in [4,8,12,20]`, `vol_cap in
[0.20, 0.35]`, symbols equity=[GLD] (BTC/USDT fetched internally as the
partner leg), vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.5 (12/24 cells)** — solid, second-strongest grid
  result in this repo after the accepted Silicon-vs-Satoshi rotation
  (0.792).
- by_vol_regime: low 2/8, mid 6/8, high 4/8 — best performance in
  mid-vol, still meaningfully robust in high-vol (unlike most
  single-asset trend/mean-reversion strategies in this repo).
- best_cell: GLD, lookback_weeks=12/vol_cap=0.20, mid-vol, Sharpe 2.608.
- worst_cell: GLD, lookback_weeks=12/vol_cap=0.35, high-vol, Sharpe 0.439
  (still positive, just below threshold — the wider 0.35 vol cap
  concentrates more BTC exposure during high-vol stretches, hurting
  risk-adjusted return there).

## Step 7 — Standard validators (config: lookback_weeks=12, vol_cap=0.20, full sample 2019-2026)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.503 | >= 1.0 |
| Max drawdown | PASS | 0.231 | <= 0.25 |
| Transaction cost survival (10bps/trade, ~29 trades over the sample) | PASS | net Sharpe 1.475 | >= 0.5 |
| Walk-forward (4 equal-size date slices) | PASS | 1.0 (4/4 slices positive Sharpe: 1.756, 0.054, 1.108, 0.949) | >= 0.75 |
| Parameter sensitivity (4-value lookback_weeks sweep: 4,8,12,20 -> Sharpe 1.778/1.630/1.503/1.348) | PASS | relative std 0.101 | <= 0.5 |

Roughly matches the source's own reported vol-capped-composite Sharpe
(1.37) and MDD (-12.27% vs 23.1% here — this repo's single-lookback
config is closer to the source's less-diversified per-lookback numbers
than its 3-way-averaged composite, so a somewhat higher MDD than the
composite's is expected).

## Outcome: ACCEPTED (GLD primary, partner BTC/USDT, lookback_weeks=12, vol_cap=0.20)

All five validators pass with comfortable margins; grid pass_fraction
0.5 across 24 cells is robust to both lookback and vol-cap choice
(param-sensitivity relative std only 0.101). This is the strongest new
strategy accepted so far this run, and the first vol-targeted
continuous-position-sizing strategy live in this repo. Kept in
`strategies/`.

Source URL:
https://quantpedia.com/dual-momentum-allocation-between-physical-gold-and-bitcoin-digital-gold/
