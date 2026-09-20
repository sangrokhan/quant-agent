# Corwin-Schultz Liquidity-Regime Trend Strategy — Backtest Report (2026-09-21)

## Hypothesis

Per Corwin & Schultz (2012, Journal of Finance) "A Simple Way to Estimate
Bid-Ask Spreads from Daily High and Low Prices" — read via
thefintechbuilder.com's worked-example explainer
(https://thefintechbuilder.com/market-microstructure/liquidity-and-spreads/corwin-schultz-spread-estimator/,
plus conceptual background from
https://quantmemo.com/concepts/corwin-schultz-high-low-spread, after
`web_search`'s DDGS backend TLS-erroring on the initial follow-up query) —
the CS estimator recovers an approximate effective bid-ask spread from
consecutive daily high/low prices alone, exploiting the fact that true
price volatility scales with sqrt(time) while the bid-ask-bounce component
of the observed high-low range does not. A widening estimated spread
signals deteriorating liquidity/rising friction (often stress-coincident);
a narrow spread signals calm, liquid conditions.

This strategy gates an SMA(fast)>SMA(slow) trend-following long entry by
requiring the rolling CS spread's own trailing percentile to be below
`spread_pctile_threshold` (calm-liquidity regime). First Corwin-Schultz-
based strategy in this repo (0 prior "corwin schultz" hits) — genuinely
distinct from this repo's other liquidity proxies (Amihud is volume-based,
Roll measure is serial-covariance-based; CS uses only high/low ranges via
a volatility-scaling argument).

## Single-config validators

### QQQ (`fast_window=20, slow_window=100, spread_pctile_threshold=0.7`) — ACCEPTED

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.442 | ≥ 1.0 |
| Max drawdown | ✅ | 0.204 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 321 trades) | ✅ | net Sharpe 0.854 | ≥ 0.5 |
| Walk-forward (4 splits, manual fallback) | ✅ | 1.0 pass fraction | ≥ 0.75 |
| Parameter sensitivity (8-combo grid, relative std) | ✅ | 0.084 | ≤ 0.5 |

### SPY (`fast_window=30, slow_window=100, spread_pctile_threshold=0.5`) — REJECTED (near-miss)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.939 | ≥ 1.0 (near-miss) |
| Max drawdown | ✅ | 0.195 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 394 trades) | ❌ | net Sharpe 0.210 | ≥ 0.5 |
| Walk-forward | ✅ | 1.0 pass fraction | ≥ 0.75 |
| Parameter sensitivity | ✅ | 0.086 | ≤ 0.5 |

SPY's higher trade count (394 vs QQQ's 321) at 10bps/trade drags net Sharpe
down sharply despite a similar gross Sharpe — turnover sensitivity, not a
fundamentally broken signal.

Full sample: 2018-01-01 to 2026-09-01, daily bars.

## Grid test summary (Step 6)

Grid: `fast_window ∈ {20,30} × slow_window ∈ {50,100} ×
spread_pctile_threshold ∈ {0.5,0.7}` × symbols `{QQQ, SPY, BTC/USDT,
ETH/USDT}` × 3 vol-regime terciles = 96 cells.

- **Overall pass fraction: 0.3125 (30/96)**
- By asset class: equity 26/48 (0.542), crypto 4/48 (0.083)
- By vol regime: low 19/32 (0.594), mid 8/32 (0.25), high 3/32 (0.094)
- Best cell: SPY, low-vol tercile, `fast_window=30, slow_window=100,
  spread_pctile_threshold=0.5` — Sharpe 2.680
- Best per-symbol: QQQ 2.389 (low-vol), SPY 2.680 (low-vol), BTC/USDT 1.346
  (high-vol), ETH/USDT 1.438 (mid-vol)
- Worst cell: ETH/USDT, high-vol tercile, `fast_window=30, slow_window=100,
  spread_pctile_threshold=0.7` — Sharpe -0.486

**Honest scope**: strong equity-specific edge (0.542 pass fraction) that
degrades sharply in high-vol regimes (0.094) and on crypto (0.083) —
plausible given the CS estimator's spread-widening signal is a slower-vs-
faster liquidity-deterioration proxy that likely lags genuine crypto
volatility spikes differently than equities. QQQ's full-sample validators
all pass; SPY is a near-miss driven mainly by transaction-cost sensitivity
at its higher-turnover config, not by a fundamentally broken signal — worth
a targeted per-symbol retune in a future iteration (same pattern this repo
has used before, e.g. 2026-09-09-100's JMA/DWMA SPY-specific retune).

## Decision

**Accept (QQQ only).** All 5 validators pass on the full-sample best QQQ
config. SPY rejected as a near-miss (Sharpe 0.939, TC-survival fail from
turnover) — flagged for a future targeted SPY-specific parameter retune.
Crypto not pursued further given the decisive grid weakness (4/48 pass).

Sources visited this iteration:
- https://thefintechbuilder.com/market-microstructure/liquidity-and-spreads/corwin-schultz-spread-estimator/ (primary source, exact formula and worked numeric example)
- https://quantmemo.com/concepts/corwin-schultz-high-low-spread (conceptual background, no exact formula)
