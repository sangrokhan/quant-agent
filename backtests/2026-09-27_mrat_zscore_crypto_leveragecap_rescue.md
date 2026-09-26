# Backtest Report: MRAT Z-Score Crypto Leverage-Cap Rescue (2026-09-27)

## Hypothesis

Direct rescue of this cron trigger's own near-miss 2026-09-27-024 (MRAT=MA(21)/
MA(200) rolling-252d-z-score threshold, source:
https://aligrithm.com/moving-average-distance-the-technical-indicator-that-passed-the-cross-section/,
Aligrithm/Ali H. Askar, summarizing Avramov/Kaplanski/Subrahmanyam's academic
"Moving Average Distance" cross-sectional factor paper). At
entry_threshold=1.0/exit_threshold=0.3/max_hold_days=60, BTC/USDT passed
Sharpe (1.012), TC-survival (1.006), walk-forward (1.0), and parameter
sensitivity (0.083) but FAILED max-drawdown (36.1% vs 25% threshold) at full
1.0x exposure. This entry scales exposure down to a fixed `leverage_cap`
whenever long (same rescue pattern already validated in this repo, e.g.
2026-09-16_trix_sizing_sma_trend_crypto_lev.py), unchanged entry/exit logic
and same source -- no new external fetch this iteration.

## Grid test summary (Step 6)

param_grid: leverage_cap=[0.3,0.4,0.5,0.6]; symbols: equity=[QQQ,SPY],
crypto=[BTC/USDT,ETH/USDT]; vol_regime_splits=3 (2018-01-01 to 2026-09-01).

- total_cells: 48, passed_cells: 26, **pass_fraction: 0.542** (up from 0.278
  in the unscaled parent entry 2026-09-27-024, confirming the leverage-cap
  fix broadly improves pass rate, not just at one cherry-picked cell)
- by_asset_class: equity 12/24, crypto 14/24
- by_vol_regime: low 16/16 (100%), mid 6/16, high 4/16
- best_cell: QQQ mid-vol leverage_cap=0.3, Sharpe=2.26 (equity inherits the
  parent entry's threshold config unchanged, leverage_cap<1.0 only dampens)
- worst_cell: QQQ high-vol leverage_cap=0.4, Sharpe=-0.57

## Single-config validators (Step 7) -- BTC/USDT and ETH/USDT, full sample

| leverage_cap | Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| 0.4 | BTC/USDT | 1.012 PASS | 0.158 PASS | 0.996 PASS | 1.0 PASS | 0.0 PASS |
| 0.5 | BTC/USDT | 1.012 PASS | 0.195 PASS | 0.999 PASS | 1.0 PASS | 0.0 PASS |
| **0.6** | **BTC/USDT** | **1.012 PASS** | **0.231 PASS** | **1.001 PASS** | **1.0 PASS** | **0.0 PASS** |
| 0.4/0.5/0.6 | ETH/USDT | 0.474 FAIL | 0.379-0.523 FAIL | 0.463-0.466 FAIL | 1.0 PASS | 0.0 PASS |

BTC/USDT clears **all 5 validators** at leverage_cap up to 0.6 (MDD 23.1%,
still under the 25% threshold with headroom to spare -- Sharpe/TC/WF are
leverage-invariant as expected since they normalize by volatility, only MDD
scales with exposure). ETH/USDT does not rescue at any leverage_cap tested
-- its underlying signal quality (Sharpe 0.474, well below 1.0) is the
binding constraint, not position sizing, consistent with 2026-09-27-024's
finding that ETH/USDT failed Sharpe/TC even before considering MDD.

## Verdict: ACCEPTED (BTC/USDT only, leverage_cap=0.6); REJECTED (ETH/USDT, all equity symbols unchanged from parent)

BTC/USDT: all 5 validators pass at leverage_cap=0.6 (max headroom before
approaching the 25% MDD ceiling; 0.4/0.5 also pass with more safety margin).
Scope is narrow -- crypto BTC/USDT only, not ETH/USDT, not equities (equity
symbols were already covered by the parent unscaled entry 2026-09-27-024 and
are unaffected by this crypto-only leverage_cap parameter). Strategy file
kept in `strategies/` as a live accepted strategy for BTC/USDT.
