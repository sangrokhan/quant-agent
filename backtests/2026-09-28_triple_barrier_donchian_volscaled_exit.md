# Triple Barrier Method (Donchian breakout + vol-scaled exit) — 2026-09-28

**Hypothesis:** Donchian 20-day-high breakout entry (200-day SMA trend gate),
exited via Lopez de Prado's Triple Barrier Method: take-profit/stop-loss set
at `entry_price * (1 +/- theta * sigma_t0)` where `sigma_t0` is the 20-day
realized daily-return std at entry, plus a fixed vertical time barrier
(`max_hold_days`). First triple-barrier/meta-labeling-family strategy in
this repo.

**Sources:** Google AI-overview summary (2026-09-28) of Lopez de Prado's
"Advances in Financial Machine Learning" framework, corroborated by
Interactive Brokers / LinkedIn (Arjun Bhandari) / Medium snippets, incl. a
worked numeric example (p0=100, sigma=2%, theta=2x -> barriers 104/96).
Direct IBKR campus article URL 404'd. `web_search` (DDGS backend) failed
with "No results found" for two queries this iteration; fell back to
`browser_exec` Google SERP per RESEARCH_LOOP.md.

## Grid test (validation/grid_test.py::run_strategy_grid)

144 cells: `theta_up` in [1.5, 2.0, 3.0] x `theta_dn` in [1.5, 2.0] x
`max_hold_days` in [10, 20], symbols equity [QQQ, SPY] + crypto
[BTC/USDT, ETH/USDT], `vol_regime_splits=3`.

- **pass_fraction: 0.368** (53/144)
- by_asset_class: equity 25/72, crypto 28/72 (roughly even)
- by_vol_regime: **low 41/48, mid 12/48, high 0/48** — strongly
  regime-concentrated
- best_cell: theta_up=3.0, theta_dn=1.5, max_hold_days=20, QQQ, low-vol
  regime, Sharpe=2.79
- worst_cell: theta_up=2.0, theta_dn=1.5, max_hold_days=20, SPY, mid-vol
  regime, Sharpe=-0.82

## Single-config validators (best grid config: theta_up=3.0, theta_dn=1.5,
max_hold_days=20, QQQ, full sample 2019-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.782 | 1.0 |
| Max drawdown | PASS | 0.133 | 0.25 |
| Transaction cost survival | PASS | 0.635 net Sharpe | 0.5 |
| Walk-forward (4 splits) | **FAIL** | 0.5 (2/4 positive) | 0.75 |
| Parameter sensitivity (grid proxy) | **FAIL** | 0.368 grid pass_fraction | 0.5 |

## Decision: REJECTED

Full-sample Sharpe and walk-forward both fail despite one very strong
isolated low-vol-regime cell (Sharpe 2.79). The vol-scaled barrier
mechanism does not generalize across volatility regimes as hypothesized —
it collapses entirely in high-vol (0/48 cells pass) and mostly fails in
mid-vol (12/48). The "volatility scaling" only helps because `sigma_t0` is
small in low-vol regimes, producing tight, survivable barriers; once
realized vol rises, the same theta multiplier produces barriers too wide
relative to the trend-following entry's typical edge, and/or the frozen
at-entry sigma estimate goes stale as the regime shifts mid-trade.

**Future rescue ideas (see notes in knowledge_base entry
2026-09-28-054):**
1. Re-estimate sigma dynamically bar-by-bar rather than freezing at entry
   (a "trailing volatility-scaled barrier" variant).
2. Add an explicit low-vol-regime entry gate (as several other accepted
   strategies in this repo do) so the strategy only trades where the grid
   shows it actually works.

Strategy file kept in `strategies/` for reference but this represents a
**rejected attempt**, not a live strategy.
