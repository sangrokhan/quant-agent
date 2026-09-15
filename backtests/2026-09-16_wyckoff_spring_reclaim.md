# Backtest report: Wyckoff Spring Reclaim (2026-09-16)

**Strategy file:** `strategies/2026-09-16_wyckoff_spring_reclaim.py`
**KB entry:** `2026-09-16-181` (rejected)

## Hypothesis

Per Wyckoff accumulation theory, a "Spring" is a deliberate shakeout below
established trading-range support that traps late sellers, followed by a
swift reclamation back above support — signaling absorption and the start
of markup. Numeric rule (per Google AI-overview synthesis of JournalPlus,
Wyckoff Analytics, TradingSim, ThinkMarkets, Trading Wyckoff, Velotrade):
rolling-window support level, breakdown bar penetrates it by
`penetration_pct`, volume condition on the breakdown bar, reclamation close
back above support within `reclaim_window_bars` bars triggers long entry.
Exit on a stop below the Spring low or a `max_hold_days` time-stop.

First Wyckoff-family strategy in this knowledge base (zero prior matches).

**Source:** Google AI-overview synthesis, read via `browser_exec` Google
SERP.

## Implementation note

Source described two alternative volume conditions for the breakdown bar
("exceptionally high/climactic" OR "markedly lower than preceding
average"). An empirical check on QQQ daily OHLCV found breakdown-bar volume
is typically **elevated** (median ratio ~1.65x range average), not
depressed — so the climactic-high-volume variant (`volume > avg*thresh`)
was used rather than the originally-hypothesized low-volume variant, which
produced zero trades everywhere.

## Grid test (Step 6)

`GridSpec(param_grid={"range_lookback": [30,40,60], "volume_ratio_thresh":
[1.3,1.5,2.0], "reclaim_window_bars": [3,5]}, symbols={"equity":
["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}, vol_regime_splits=3)` —
216 cells, 2018-01-01 to 2026-09-01.

| metric | value |
|---|---|
| pass_fraction | 16/216 = 0.074 |
| by_asset_class | equity 12/108, crypto 4/108 |
| by_vol_regime | low 10/72, mid 6/72, **high 0/72** |
| best cell | QQQ, range_lookback=30/volume_ratio_thresh=1.5/reclaim_window_bars=3, low-vol regime, Sharpe **1.592** |
| worst cell | SPY, range_lookback=30/volume_ratio_thresh=1.3/reclaim_window_bars=3, mid-vol regime, Sharpe -1.445 |

All passes are concentrated in the low/mid vol-regime tercile slices for
equities — zero passes in the high-vol regime and only 4/108 in crypto.

## Single-config validators (best grid config, full-sample QQQ)

`range_lookback=30, volume_ratio_thresh=1.5, reclaim_window_bars=3, max_hold_days=20`

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | ❌ | -0.007 | 1.0 |
| max_drawdown | ❌ | 0.350 | 0.25 |
| transaction_cost_survival | ❌ | -0.049 | 0.5 (24 trades, 15bps/trade) |

The full-sample single-config numbers decisively fail — the grid's
best-cell Sharpe of 1.59 only holds within the narrow low-vol-regime
tercile slice, not across the full sample. This is the opposite of a
robust "narrower-but-honest" acceptance (c.f. RESEARCH_LOOP.md Step 6
guidance) — the full-sample result is actively negative/high-drawdown, so
the regime-slice outperformance looks like overfitting to a favorable
sub-period rather than a genuine, tradeable regime-dependent edge.

Walk-forward validator hit an unrelated pre-existing vectorbt API
incompatibility (`vbt.utils.splitting` not found in this environment's
vectorbt version) — not run; the full-sample Sharpe/MDD/TC-survival triple
failure already makes the accept/reject call decisive without it.

## Decision

**Rejected.** Full-sample Sharpe negative and MDD 0.35 (well over the 0.25
threshold) for even the grid's best-performing cell. The 7.4% overall grid
pass fraction is concentrated in low-vol regime slices only, with zero
high-vol-regime passes — consistent with overfitting to a favorable
sub-period rather than a genuine edge.
