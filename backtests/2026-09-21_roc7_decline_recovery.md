# ROC(7) Sharp-Decline / Sharp-Recovery Strategy — Backtest Report (2026-09-21)

## Hypothesis

Per QuantifiedStrategies' Facebook video ("A 71.2% win rate came from one
indicator and two simple thresholds", read via `browser_exec` after
`web_search`'s DDGS backend TLS-erroring on the follow-up query): a
backtested Rate-of-Change strategy on SPY (1993-2026) claims 146 trades,
71.2% win rate, 2.40 profit factor, $1->$9.15, 29% max drawdown, using:
1. ROC(7) closes below -3% → buy SPY at the next open
2. ROC(7) closes above +3% → sell SPY at the next open

Adapted to this repo's daily-bar `position.shift(1)` execution convention
(rather than literally modeling open-vs-close timing). Distinct from the
33 prior ROC-based entries in this repo (none use this exact symmetric
±3% ROC(7) threshold entry/exit design).

## Single-config validators (grid-best config: QQQ, `roc_window=5,
entry_threshold=-3.0, exit_threshold=4.0`)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.522 | ≥ 1.0 |
| Max drawdown | ❌ | 0.444 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 166 trades) | ❌ | net Sharpe 0.481 | ≥ 0.5 |
| Walk-forward (4 splits, manual fallback) | ✅ | 1.0 pass fraction | ≥ 0.75 |
| Parameter sensitivity (12-combo grid, relative std) | ✅ | 0.189 | ≤ 0.5 |

Full sample: 1998-01-01 to 2026-09-01, daily bars.

## Grid test summary (Step 6)

Grid: `roc_window ∈ {5,7,10} × entry_threshold ∈ {-3.0,-4.0} ×
exit_threshold ∈ {3.0,4.0}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3
vol-regime terciles = 144 cells.

- **Overall pass fraction: 0.0139 (2/144)** — decisively weak
- By asset class: equity 2/72 (0.028), crypto 0/72 (0.0, decisive reject)
- By vol regime: low 1/48, mid 1/48, high 0/48
- Best cell: QQQ, low-vol tercile, `roc_window=5, entry_threshold=-3.0,
  exit_threshold=4.0` — Sharpe 1.384
- Worst cell: BTC/USDT, low-vol tercile, `roc_window=5,
  entry_threshold=-4.0, exit_threshold=3.0` — Sharpe -0.879

**Honest scope**: the source's own headline stats (71.2% win rate, 2.40
profit factor over the full 1993-2026 SPY sample) do not survive this
repo's stricter full-sample Sharpe/MDD/TC-cost bar once measured on
daily-bar `shift(1)` execution rather than the source's literal next-open
timing, and once tested across a param grid rather than the single
hand-picked (7, -3%, +3%) combination. A high win rate with a large
max-drawdown (44% here vs the source's own reported 29%) and mediocre
Sharpe is consistent with a strategy that wins often but with an
asymmetric large-loss tail — the single-config full-sample numbers make
that concrete.

## Decision

**Reject.** 3 of 5 full-sample validators fail (Sharpe, MDD, TC-survival).
Strategy file and report kept as a record of a rejected attempt.

Sources visited this iteration:
- https://www.facebook.com/QuantifiedStrategies/videos/a-712-win-rate-came-from-one-indicator-and-two-simple-thresholds-most-traders-wo/2299239730813479/ (primary source, browser_exec, exact rules and headline stats disclosed)
- (Also checked and skipped as saturated this iteration: Ehlers Roofing Filter (20 prior entries), Klinger Oscillator (28 prior entries), Andean Oscillator (4 prior entries), Murrey Math (1 prior, already rejected), Connors VIX RSI (already tried near-miss 2026-09-05-052), Larry Connors RSI(2)+200SMA (already accepted 2026-09-03-005), Capturing Short-Term Reversals SPY/VIX Medium article (identical to already-accepted 2026-09-03-005))
