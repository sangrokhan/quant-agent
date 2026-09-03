# knowledge_base/strategies_log.jsonl

Append-only log of every strategy hypothesis the Research Agent has tried,
one JSON object per line (JSONL), regardless of pass/fail outcome. This is
the "memory" that prevents re-testing the same idea and that the novelty
check (see RESEARCH_LOOP.md) reads before formulating a new hypothesis.

## Schema (one JSON object per line)

```json
{
  "id": "string, e.g. 2026-09-03-001 (date + sequence within that date)",
  "created_at": "ISO8601 UTC timestamp",
  "hypothesis": "one or two sentence plain-English statement of the idea being tested",
  "asset_class": "equity | crypto | fx | ... (free text, keep short)",
  "symbols": ["list", "of", "tickers/pairs", "used"],
  "timeframe": "e.g. 1d, 1h",
  "strategy_file": "relative path under strategies/, or null if rejected before implementation",
  "backtest_report": "relative path under backtests/, or null if rejected before a full backtest ran",
  "validators": {
    "sharpe_ratio": {"passed": true, "value": 1.42, "threshold": 1.0},
    "max_drawdown": {"passed": true, "value": 0.18, "threshold": 0.25},
    "transaction_cost_survival": {"passed": true, "value": 0.91, "threshold": 0.5},
    "walk_forward": {"passed": false, "value": 0.5, "threshold": 0.75},
    "parameter_sensitivity": {"passed": true, "value": 0.31, "threshold": 0.5}
  },
  "outcome": "accepted | rejected",
  "rejection_reason": "string, or null if accepted",
  "notes": "free text: anything future loops should know (edge cases, data quirks, near-misses worth revisiting with a tweak, etc.)"
}
```

Field notes:
- `outcome: "accepted"` means all validators the Research Agent judged
  relevant passed, and the strategy file + backtest report were kept.
- `outcome: "rejected"` still gets a full entry — recording failed ideas is
  the entire point of this file (avoid repeating them).
- `validators` may omit keys that weren't run for a given hypothesis (e.g. a
  hypothesis rejected at the novelty-check stage, before any backtest, can
  have `validators: {}`).

## Sample entries

```json
{"id": "2026-09-01-001", "created_at": "2026-09-01T02:15:00Z", "hypothesis": "SPY 20/50-day SMA crossover with volume confirmation outperforms buy-and-hold on a 5-year window.", "asset_class": "equity", "symbols": ["SPY"], "timeframe": "1d", "strategy_file": "strategies/2026-09-01_sma_crossover_spy.py", "backtest_report": "backtests/2026-09-01_sma_crossover_spy.md", "validators": {"sharpe_ratio": {"passed": true, "value": 1.15, "threshold": 1.0}, "max_drawdown": {"passed": true, "value": 0.21, "threshold": 0.25}, "transaction_cost_survival": {"passed": true, "value": 0.87, "threshold": 0.5}, "walk_forward": {"passed": false, "value": 0.5, "threshold": 0.75}, "parameter_sensitivity": {"passed": true, "value": 0.28, "threshold": 0.5}}, "outcome": "rejected", "rejection_reason": "failed walk-forward robustness (only 2 of 4 out-of-sample splits had positive Sharpe); looked good only in-sample.", "notes": "Full-period Sharpe was attractive but walk-forward exposed regime-dependence around 2022 rate-hike period. Consider revisiting with a volatility-regime filter rather than dropping the idea entirely."}
{"id": "2026-09-02-001", "created_at": "2026-09-02T04:40:00Z", "hypothesis": "BTC/USDT funding-rate-extreme mean reversion (long when funding < -0.01%, flat otherwise) has positive edge on 1h bars.", "asset_class": "crypto", "symbols": ["BTC/USDT"], "timeframe": "1h", "strategy_file": null, "backtest_report": null, "validators": {}, "outcome": "rejected", "rejection_reason": "novelty check: near-duplicate of nothing in this log yet, but current data/loaders.py + ccxt provider does not expose funding-rate data, only OHLCV. Rejected at feasibility stage before implementation.", "notes": "Would need a ccxt funding-rate fetch helper added to data/loaders.py in a future loop before this hypothesis can be tested."}
```

Keep entries append-only — never rewrite or delete a prior line, even for a
strategy that later gets superseded (add a new entry referencing the old
`id` in `notes` instead).
