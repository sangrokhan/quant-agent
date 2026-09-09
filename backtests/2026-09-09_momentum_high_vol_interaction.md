# 2026-09-09 — Momentum × High-Volatility Interaction (rejected)

**Hypothesis** (id `2026-09-09-111`): Time-series adaptation of Quantpedia's
"Momentum and Reversal Combined with Volatility Effect in Stocks"
(https://quantpedia.com/strategies/momentum-and-reversal-combined-with-volatility-effect-in-stocks,
source paper: Wei, "Do Momentum and Reversals Coexist?", 1964-2009 cross-sectional
US large-cap study, reported 16.46% p.a. long-short, Sharpe 0.65). Source finding:
momentum returns are STRONGER, not weaker, in the highest-realized-volatility
quintile (information-uncertainty / under-reaction rationale). Adapted here as a
single-asset time-series long-only strategy: go long when trailing
`formation_window`-day return is positive AND the asset's own realized volatility
ranks at/above `vol_percentile_threshold` percentile of its trailing 252-day
history (elevated-vol regime as an entry GATE for momentum, not a sizing
dampener — distinct from previously-rejected 2026-09-03-003 which used
inverse-vol as a position-SIZE overlay).

Strategy file: `strategies/2026-09-09_momentum_high_vol_interaction.py`

## Step 6 grid summary (formation_window ∈ {63,126,189} × vol_percentile_threshold ∈ {0.5,0.7} × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles, 72 cells)

- `pass_fraction`: 0.222 (16/72)
- `by_asset_class`: equity 16/36 passed, crypto 0/36 passed (decisive crypto failure)
- `by_vol_regime`: low 12/24, mid 4/24, high 0/24 passed — **note the irony**: the
  strategy is gated to trade only in HIGH realized-vol regimes (per the source's
  own hypothesis), yet it passes SHARPE/MDD thresholds almost exclusively in the
  underlying asset's LOW-vol regime slices and fails 0/24 in high-vol slices —
  the opposite of what the source's cross-sectional finding would predict for a
  time-series analog.
- `best_cell`: formation_window=63, vol_percentile_threshold=0.5, SPY, low-vol
  regime, Sharpe 2.05
- `worst_cell`: formation_window=63, vol_percentile_threshold=0.7, QQQ, high-vol
  regime, Sharpe -0.64

## Single-config validators (best grid config: formation_window=63, vol_percentile_threshold=0.5), full 2019-2026 sample

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.310 ❌ | 0.576 ❌ | ≥ 1.0 |
| Max drawdown | 0.252 ❌ | 0.193 ✅ | ≤ 0.25 |
| TC survival (10bps/trade) | 0.244 ❌ | 0.490 ❌ | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-slice fallback — `vbt.utils.splitting` broken in this install) | 0.50 ❌ | 0.75 ✅ | ≥ 0.75 pass fraction |
| Trades | 40 | 33 | — |

## Verdict: **reject** (both QQQ and SPY)

Full-sample Sharpe fails decisively for both symbols (well under the 1.0
threshold despite an eye-catching best-grid-cell Sharpe of 2.05 in low-vol
SPY slices only). Crypto fails 0/36 grid cells entirely. TC-survival fails
both equities. The grid's own `by_vol_regime` breakdown directly falsifies
the adapted hypothesis: this time-series construction only works in LOW-vol
regimes, the opposite of the source's cross-sectional high-vol-quintile
finding — the cross-sectional "high information uncertainty" effect (relative
ranking of stocks by vol within a universe) does not translate to a
single-asset "current vol regime vs its own history" time-series gate.
