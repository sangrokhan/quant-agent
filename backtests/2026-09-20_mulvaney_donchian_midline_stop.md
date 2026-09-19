# Mulvaney-replica Donchian(126) breakout with midline trailing stop — ACCEPTED (QQQ only)

**Hypothesis source:** Concretum Research's reverse-engineering of Paul
Mulvaney Capital Management's systematic trend-following CTA approach
(https://the7circles.uk/trade-like-mulvaney/, read via `browser_exec` after
the original Concretum Substack articles proved inaccessible in a prior
iteration — `web_search` returned no results/TLS errors on this iteration's
queries). Fitting 4,320 synthetic CTA trend programs against MCM's monthly
returns (R² 0.71-0.73, best-fit configuration) found: 126-trading-day
(~6-month) Donchian breakout entries, the Donchian channel MIDLINE as the
trailing stop (widens automatically with volatility, no separate ATR
multiplier), and an initial stop offset by one-third of the channel range
from entry (tighter early risk, consistent with Mulvaney's own description).

This repo has extensively tested Donchian breakout/pullback/slope
variants, but never this specific long-term (126-day) breakout + midline
TRAILING STOP construction, directly reverse-engineered from a real,
still-operating CTA fund.

## Grid test (Step 6)

`donchian_window ∈ {63, 100, 126, 160} × initial_stop_frac ∈ {0.25, 0.333, 0.5}`,
symbols = QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3,
144 total cells.

- **pass_fraction: 0.299** (43/144 cells passed)
- **by_asset_class:** equity 30/72, crypto 13/72
- **by_vol_regime:** low 37/48, mid 6/48, **high 0/48** — the strategy does
  not survive high-realized-vol regimes (consistent with a slow, wide-stop
  trend system being whipsawed in choppy/volatile conditions)
- **best_cell:** SPY, donchian_window=63/initial_stop_frac=0.333, low-vol
  tercile, Sharpe 2.84 (single-tercile, cherry-picked)

## Single-config validation (Step 7) — QQQ, donchian_window=126 (source's own value), initial_stop_frac=0.333

| Validator | Result | Threshold | Pass? |
|---|---|---|---|
| Sharpe ratio (full period 2019-2026) | 1.021 | ≥ 1.0 | **PASS** |
| Max drawdown | 0.153 | ≤ 0.25 | **PASS** |
| Transaction-cost survival (10bps/trade, 17 trades) | net Sharpe 1.000 | ≥ 0.5 | **PASS** |
| Walk-forward (4 contiguous splits, manual) | 4/4 splits positive (1.00) | ≥ 0.75 | **PASS** |
| Parameter sensitivity (25-cell donchian_window×initial_stop_frac sweep) | relative_std 0.115 | ≤ 0.5 | **PASS** |

All 5 validators pass cleanly for QQQ at the source's own disclosed
parameter (donchian_window=126). SPY at the same config: Sharpe 0.851
(near-miss below 1.0 threshold), MDD 0.134 (pass), TC net Sharpe 0.816
(pass) — SPY narrowly misses on Sharpe alone. Crypto is a decisive
rejection: BTC/USDT Sharpe 0.233/MDD 0.427, ETH/USDT Sharpe 0.186/MDD
0.593.

## Verdict: ACCEPTED (QQQ only)

The strategy is accepted for QQQ at the source's own disclosed parameters
(donchian_window=126, initial_stop_frac=1/3), with only 17 trades over the
7.7-year sample (a genuinely low-turnover, long-hold trend system
consistent with Mulvaney's own ~6-month average holding period). SPY is a
near-miss (Sharpe 0.851 vs 1.0 threshold) and is NOT accepted; crypto is
decisively rejected (fails all metrics by a wide margin, likely because
BTC/ETH's much higher baseline volatility makes the 1/3-range initial stop
too loose relative to daily price swings, and the strategy has no
volatility-regime gate to sit out crypto's characteristic high-vol
whipsaw periods). This QQQ-only scope should be recorded precisely in the
knowledge base so future iterations don't over-trust it on SPY or crypto.
