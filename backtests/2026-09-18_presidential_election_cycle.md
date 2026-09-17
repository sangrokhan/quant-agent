# Backtest Report: 4-Year US Presidential Election Cycle Seasonality (rejected)

**Strategy file:** `strategies/2026-09-18_presidential_election_cycle.py`
**Knowledge base id:** 2026-09-18-023

## Hypothesis

Per a Google AI-overview synthesis of SoFi/CFA Institute/Modern Wealth
Management/BMO explainers of Yale Hirsch's Presidential Election Cycle
Theory (visited this iteration; `web_search` returned normal results for
initial keyword discovery, no fallback needed), the pre-election year (year
3 of a 4-year US presidential term) has historically been the S&P 500's
strongest year (source claims ~78-82% win rate, ~15-17% average annual
return vs ~10% overall), attributed to expansionary fiscal/monetary policy
ahead of elections. Tested: long only during pre-election calendar years
(optionally also holding through the following election year per the
source's secondary ~6-8%-average finding), flat otherwise.

## Single-config metrics (full sample, 1995-2026 for SPY; QQQ from its
inception within that window)

| Symbol | Config | Sharpe | MDD | Net Sharpe (10bps) | Trades |
|---|---|---|---|---|---|
| QQQ | pre-election only | 0.864 (fail, thr 1.0) | 0.171 (pass) | 0.861 (pass) | 6 |
| QQQ | + election year | 0.530 (fail) | 0.583 (fail, thr 0.25) | 0.529 (pass) | 6 |
| SPY | pre-election only | 0.598 (fail) | 0.199 (pass) | 0.595 (pass) | 7 |
| SPY | + election year | 0.473 (fail) | 0.518 (fail) | 0.471 (pass) | 7 |

## Step 6 grid summary (also_hold_election_year in [False, True],
symbols=QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

```
total_cells: 24, passed_cells: 4, pass_fraction: 0.167
by_asset_class: equity 3/12, crypto 1/12
by_vol_regime: low 3/8, mid 1/8, high 0/8
best_cell: ETH/USDT mid-vol, also_hold_election_year=True, Sharpe=2.18
worst_cell: ETH/USDT high-vol, also_hold_election_year=False, Sharpe=-0.95
```

The grid's isolated per-vol-regime cells occasionally clear the Sharpe bar
(mostly low-vol equity slices and one crypto mid-vol slice), but this
strategy's full-sample -- the economically meaningful evaluation window for
a multi-year political cycle theory, since a 4-year-cycle strategy sliced
into single-year vol regimes is a statistically thin/likely-spurious
sub-sample -- Sharpe never reaches 1.0 on either equity symbol.

## Pass/fail per validator (best full-sample config: pre-election-only,
QQQ)

- Sharpe ratio: **fail** (0.864 < 1.0)
- Max drawdown: pass (0.171 < 0.25)
- Transaction cost survival: pass (0.861 >= 0.5, only 6 trades total makes
  this an easy bar to clear)
- Walk-forward / parameter sensitivity: not run -- rejected at the primary
  Sharpe gate before further validator spend, per RESEARCH_LOOP.md Step 7's
  minimum-bar guidance.

## Decision

**Rejected** across all symbols and both configs. QQQ pre-election-only was
the closest (Sharpe 0.864) but still a genuine miss, not a borderline
near-miss worth an immediate parameter-retune sub-iteration (there are no
tunable parameters here beyond the binary "also hold election year" switch
and the calendar-boundary months, and both already tested). Also note this
strategy trades only 6-7 times total over a 25-30 year full-sample window --
an inherently very low-power test for any statistical claim, a structural
limitation of any multi-year political-cycle strategy tested on a single
symbol's daily bars rather than a genuine defect in the source's own
historical claim.
