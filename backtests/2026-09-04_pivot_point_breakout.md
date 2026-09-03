# Daily Pivot Point (P) Breakout — Backtest Report

**Hypothesis:** Per ProTradingSchool's Pivot Points strategy guide, a close
crossing above the classic floor-trader pivot point (P, R1, or S1, derived
from the PRIOR day's high/low/close) signals a new uptrend emerging, worth
a long entry; exit when close crosses back below the pivot point (P). First
strategy in this repo using no rolling smoothing window at all — a single
prior bar's algebraically-derived level, recomputed fresh every bar.

Source: https://www.protradingschool.com/the-pivot-points-strategy/
(full formula given directly, no extract/browser fallback needed).

## Step 6 — Grid test (entry_level x asset class x vol regime)

Grid: `entry_level` in [P, R1, S1] (all exit at P), symbols
equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3.
36 cells total.

- **pass_fraction: 0.222 (8/36)**
- by_asset_class: equity 8/18 passed; crypto 0/18 (decisive reject)
- by_vol_regime: low 6/12; mid 2/12; high 0/12
- best_cell: QQQ, entry_level=R1, vol_regime=low, Sharpe 2.56 (single
  low-vol tercile only, not full-sample)

## Step 7 — Full-sample Sharpe across all entry-level variants (QQQ, SPY)

| Config | QQQ Sharpe | SPY Sharpe |
|---|---|---|
| P -> P | 0.331 | 0.085 |
| R1 -> P | 0.492 | 0.164 |
| S1 -> P | 0.711 | **0.788** (best overall) |

**No combo on either symbol clears the 1.0 Sharpe threshold on the full
sample** — the grid's attractive-looking low-vol-tercile cells (Sharpe
>2.5) do not generalize once the full multi-regime sample is used, a
textbook overfitting-to-a-slice pattern this repo has seen before.

## Single-config validation (best full-sample config: SPY, entry_level=S1, exit_level=P)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.788 | 1.0 |
| Max drawdown | ❌ | 0.263 | 0.25 |
| Transaction cost survival (10bps/trade, 301 trades) | ❌ | 0.346 | 0.5 |

301 round-trip trades over 7.7yr (~1 trade every 6.6 trading days) — the
pivot level is crossed far too often on daily bars to generate a
meaningfully filtered signal; transaction costs alone erode most of the
already-marginal edge.

## Outcome

**Rejected across all asset classes/configs.** No config reaches the
Sharpe threshold on the full sample; the best (SPY S1->P) additionally
fails max drawdown and transaction-cost survival due to very high trade
frequency. Crypto rejected decisively (0/18 grid cells).
