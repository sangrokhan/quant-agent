# 2026-09-21 Paroli-Style Streak Sizing on SMA(200) Trend Gate

**Hypothesis:** Per quantifiedstrategies.com's "Paroli Strategy in Trading"
article (https://www.quantifiedstrategies.com/paroli-strategy-in-trading/,
read via browser_exec — web_search DDGS backend returned "No results found"
this iteration), a Paroli/anti-Martingale positive-progression position-size
overlay (step exposure up after a win, reset after a loss, capped at N
consecutive step-ups) on top of an existing edge (SMA(200) trend-following
gate) either preserves/improves risk-adjusted performance, or — per the
source's own stated verdict that "Paroli can change the shape of returns
but cannot create an edge on its own" — simply reshapes the path without
improving expected value.

**Strategy file:** `strategies/2026-09-21_paroli_streak_sizing_sma_trend.py`

## Single-config validator results (best config: base_unit=1.0,
step_multiplier=1.5, max_steps=2, trend_window=200, leverage_cap=1.0)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.140 (pass, thr 1.0) | 0.219 (pass, thr 0.25) | 1.103 (pass, thr 0.5) | 1.0 pass_fraction (pass, thr 0.75) | 0.011 rel-std (pass, thr 0.5) |
| SPY | 0.822 (fail, thr 1.0) — best combo (base_unit=0.5) reaches 0.943, still fails | 0.208 (pass) | n/a | n/a | n/a |

## Step 6 grid summary (base_unit∈{0.5,1.0} × step_multiplier∈{1.5,2.0} ×
max_steps∈{2,3} × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles)

- total_cells: 96, passed_cells: 28, **pass_fraction: 0.292**
- by_asset_class: equity 24/48 passed, crypto 4/48 passed
- by_vol_regime: low 18/32, mid 10/32, **high 0/32** (strategy structurally
  fails in high-realized-vol regimes across every symbol/param combo)
- best_cell: SPY low-vol tercile, base_unit=1.0/step_multiplier=1.5/
  max_steps=2, Sharpe 2.854
- worst_cell: ETH/USDT high-vol tercile, Sharpe 0.042

## Key finding (validates the source's own claim)

Sweeping `step_multiplier` (1.5 vs 2.0) and `max_steps` (2 vs 3) produced
**zero variance** in full-sample Sharpe/MDD for both QQQ and SPY — only
`base_unit` (a flat leverage multiplier) moved the numbers at all. This is
because the SMA(200) trend gate produces few directional flips and the
underlying strategy return series rarely strings together the kind of
persistent daily win/loss runs needed for the progression to reach step 2
or 3 before resetting. In other words: **the Paroli overlay never actually
gets to exercise its own progression logic often enough to matter** — it
collapses to a fixed base_unit multiplier in practice, directly confirming
the source's stated mathematical argument that positive-progression sizing
"only reshapes the path... it does not change expected value" — here it
doesn't even reliably reshape the path, because trend-following entries
are too infrequent for meaningful streaks to accumulate.

## Decision: ACCEPT (QQQ only)

QQQ passes all 5 validators at base_unit=1.0/step_multiplier=1.5/
max_steps=2 (Sharpe 1.140, MDD 0.219, TC-survival 1.103, walk-forward
1.0, parameter-sensitivity 0.011 — extremely low, confirming the
step_multiplier/max_steps insensitivity finding above). SPY near-misses
(best 0.943, base_unit=0.5). Crypto rejected decisively (grid pass_fraction
4/48, worst in high-vol regime as with equities).
