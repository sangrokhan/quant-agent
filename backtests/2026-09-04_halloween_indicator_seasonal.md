# Backtest Report: Halloween Indicator / Sell-in-May Seasonal Switch

**Strategy file:** `strategies/2026-09-04_halloween_indicator_seasonal.py`
**Hypothesis ID:** 2026-09-04-104
**Source:** Google search corroboration (Capital.com/ResearchGate/Emerald/Marotta-on-Money snippets) — Bouman & Jacobsen (2002) "Sell in May and Go Away" academic literature.

## Hypothesis

The Halloween Indicator: equities historically earn nearly all long-run
gains during Nov-Apr ("best six months"), with May-Oct contributing
little/nothing. Fixed calendar-only rule, no technical indicator.

## Single-config validators (primary config: best_start_month=10, best_end_month=3, SPY, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.58 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.341 | ≤ 0.25 | **FAIL** |
| Transaction cost survival (10bps/trade, 7 trades) | net Sharpe 0.57 | ≥ 0.5 | PASS |
| Walk-forward (4 contiguous splits, manual) | 3/4 splits positive Sharpe (0.75) | ≥ 0.75 | PASS |
| Parameter sensitivity (start/end month grid) | 0.192 | ≤ 0.5 | PASS |

## Step 6 grid summary (best_start_month∈{10,11} × best_end_month∈{3,4}, SPY+QQQ+BTC/USDT+ETH/USDT, vol_regime_splits=3)

- Total cells: 48, passed: 8, **pass_fraction = 0.167**
- By asset class: equity 8/24 (33%), crypto 0/24 (0%) — crypto falsification check confirms no transfer, consistent with the effect's fiscal-year/tax-loss-harvesting behavioral explanation not applying to a 24/7 market with no such institutional cycle.
- By vol regime: low 8/16 (50%), mid 0/16, high 0/16.
- Best cell: best_start_month=10, best_end_month=3, SPY, low-vol, Sharpe 2.14.

## Decision: REJECTED

Full-sample Sharpe (0.58) and MDD (0.34) both fail thresholds on the
best-performing config. Grid pass_fraction (16.7%) is weak and concentrated
entirely in equity/low-vol cells; crypto (0/24) confirms no cross-asset
transfer, which is consistent with the mechanism the source itself
proposes (institutional fiscal-year effects) but doesn't rescue the
equity-side result, which itself is too weak on this 2019-2026 sample
(only 7 semi-annual switches, high sampling variance) to clear the bar.
