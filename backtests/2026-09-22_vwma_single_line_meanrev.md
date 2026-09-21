# 2026-09-22 — Single-Line VWMA Mean-Reversion (Source's "Strategy 1")

**Source:** https://www.quantifiedstrategies.com/vwap-trading-strategy/
(QuantifiedStrategies.com's own disclosed SPY VWAP-moving-average backtest,
"Strategy 1")

**Hypothesis:** Per the source's own disclosed rule: buy at close when
close crosses below the N-day VWMA (volume-weighted moving average), sell
when close crosses back above it. Source's own results table shows short
N (5-day) performs best for this mean-reversion framing (CAGR 8.18% vs
2.67-2.93% at N=100-200). Distinct from this repo's already-accepted dual
fast/slow VWMA crossover (2026-09-04-060, a momentum/trend framing using
TWO VWMA lines) — here it's a single VWMA line crossed against price
itself, mean-reversion framing.

## Grid test (Step 6)

`vwma_window` in [5, 10, 25] x `max_hold_days` in [5, 10, 20], symbols
QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto), vol_regime_splits=3,
2018-01-01 to 2026-09-01. 108 total cells.

- pass_fraction: 0.111 (12/108)
- by_asset_class: equity 12/54, crypto 0/54 (decisive reject)
- by_vol_regime: low 9/36, mid 0/36, high 3/36 — very narrow edge,
  concentrated almost entirely in low-vol regime
- best_cell: SPY, vwma_window=5/max_hold_days=5, low-vol regime, Sharpe
  1.710
- Best average equity config: vwma_window=5, max_hold_days=20 (mean Sharpe
  0.879 across 6 equity cells)

## Single-config validators (Step 7): vwma_window=5, max_hold_days=20

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.926 **FAIL** | 0.648 **FAIL** |
| Max drawdown (<=0.25) | 0.226 PASS | 0.216 PASS |
| TC survival (net Sharpe >=0.5, 10bps, 569/573 trades) | 0.323 **FAIL** | 0.061 **FAIL** |
| Walk-forward (4-split, >=0.75 pass) | 1.0 PASS | 0.75 PASS |
| Parameter sensitivity (relative_std <=0.5) | 0.686 **FAIL** | 9.206 **FAIL** |

## Decision: REJECTED

Decisive rejection on both QQQ and SPY. The short 5-day VWMA crossunder/
crossover trigger fires extremely frequently (569-573 position changes over
~2178 trading days — essentially a coin-flip-frequency mean-reversion
churn), which crushes transaction-cost survival (net Sharpe drops to
0.32/0.06 after just 10bps/trade) even though the raw signal (before costs)
has some structure (Sharpe 0.93/0.65, still below the 1.0 threshold
anyway). Parameter sensitivity is also very poor, especially on SPY
(relative_std 9.2 — Sharpe swings from strongly negative to strongly
positive depending on vwma_window/max_hold_days). Crypto decisively
rejected (0/54).

**Note for future loops:** the source's own results table actually favors
this Strategy-1 framing being tested with a HOLD-N-DAYS exit rather than a
signal-based exit (that's literally the source's "Strategy 3" variant,
evaluated by avg gain/trade rather than CAGR) — this repo's current
implementation uses a signal-based exit (crossback above VWMA) plus a
time-stop, which produces far more round-trips than a pure N-day-hold
would. A fixed N-day-hold exit (no early signal-based exit) is worth
testing separately as this repo has a similar existing pattern (see
McGinley Dynamic fixed-hold strategy, rejected but instructive) — reducing
trade count that way could rescue the TC-survival failure. Not pursued this
iteration to keep scope tight; flagged as a concrete follow-up.
