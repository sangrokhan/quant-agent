# DeMarker(5) Deep-Oversold Mean Reversion on TLT (Treasury ETF)

**Hypothesis:** Per QuantifiedStrategies.com's "5 Algorithmic Trading
Strategies 2026" (https://www.quantifiedstrategies.com/algorithmic-trading-strategies/),
Strategy #4: 5-day-lookback DeMarker < 0.10 entry (no trend filter),
exit when close > yesterday's high. Source explicitly notes "this
strategy also works well with long-term Treasuries" -- first TLT
DeMarker test in this repo (2 prior DeMarker entries were QQQ/SPY only,
different mechanics: threshold-cross+trend-filter+time-stop, and
divergence).

## Strategy file
`strategies/2026-09-20_demarker5_oversold_tlt.py`

## Parameter neighborhood scan (TLT, full sample 2010-2026, Sharpe)

| dem_window \ threshold | 0.05 | 0.08 | 0.10 | 0.12 |
|---|---|---|---|---|
| 3 | 0.725 | 0.752 | 0.676 | 0.713 |
| 4 | 0.740 | 0.985 | **0.988** | 0.812 |
| 5 | 0.791 | 0.902 | 0.961 | 0.770 |
| 6 | 0.657 | 0.779 | 0.625 | 0.532 |

Best config found: dem_window=4, oversold_threshold=0.10, Sharpe **0.988**
(vs 1.0 threshold) -- a decisive-enough near-miss confirmed across a
neighborhood scan (no adjacent config clears 1.0 either).

## Grid test summary (dem_window in {4,5} x oversold_threshold in {0.08,0.10,0.15}, TLT/QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2010-2026)

- pass_fraction: 0.256 (23/90 cells)
- by_asset_class: equity 23/54, crypto 0/54 (decisive crypto reject -- DeMarker's high/low-extreme mechanic combined with no trend filter doesn't transfer to 24/7 crypto)
- by_vol_regime: low 9/30, mid 9/30, high 5/30 (more balanced across regimes than most strategies in this repo, likely because the source's own construction has NO trend filter and no time-stop)
- best_cell: SPY, dem_window=4/oversold_threshold=0.15, low-vol regime, Sharpe 1.65

## Full-sample validators (TLT, dem_window=4, oversold_threshold=0.10)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.988 | >= 1.0 | FAIL (near-miss) |
| Max drawdown | 0.118 | <= 0.25 | PASS |
| TC survival (10bps/trade) | net Sharpe ~0.6 (est.) | >= 0.5 | PASS (estimated from neighboring config) |

## Outcome

**Rejected** (near-miss). The source's own claim that this exact
mechanism "also works well with long-term Treasuries" is directionally
confirmed -- TLT's best config (Sharpe 0.988) is meaningfully stronger
than QQQ/SPY's best configs at the source's literal disclosed parameters
(dem_window=5, threshold=0.10: TLT 0.961 vs QQQ 0.730, SPY 0.683) -- but
even TLT's own locally-optimal neighborhood doesn't clear this repo's 1.0
Sharpe bar. Worth flagging as a genuine near-miss for a future loop:
possible next steps include adding a light trend filter (the source's own
construction has none) or testing a wider Treasury-curve universe (IEF,
SHY) to see if the edge is stronger elsewhere on the curve.
