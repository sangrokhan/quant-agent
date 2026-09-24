# MACD Histogram 4-Day Declining-Momentum Exhaustion (QQQ)

**Hypothesis:** Per QuantifiedStrategies.com "MACD Histogram Trading Strategy"
(accessed via Google AI-overview cached snippet, browser_exec fallback --
web_search DDGS backend errored on this iteration's query, live page itself
returns 404), a mean-reversion long entry fires when the standard
MACD(12,26,9) histogram has declined for 4 consecutive bars AND the
histogram value 4 bars ago was already negative AND today's close is below
yesterday's close. Exit ("QS exit") on the first close above the prior
day's high, backstopped here by a max_hold_days time-stop.

Source: https://www.quantifiedstrategies.com/macd-histogram-trading-strategy/
(cached Google AI-overview snippet; live page 404s)

## Grid test summary (equity only, light workload)

- Grid: `hist_decline_days` in {3,4,5} x `max_hold_days` in {7,10}, QQQ+SPY,
  3 vol regimes (low/mid/high) = 36 cells.
- pass_fraction = 0.444 (16/36)
- by_vol_regime: low 8/12, mid 6/12, high 2/12 (works best in calmer markets)
- best_cell: hist_decline_days=3, max_hold_days=10, QQQ, low-vol, Sharpe 1.837
- best avg-across-vol-regime config: hist_decline_days=3, max_hold_days=10,
  QQQ, avg Sharpe 1.347

## Single-config validators (QQQ, hist_decline_days=3, max_hold_days=10)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.012 | >= 1.0 |
| Max drawdown | **FAIL** | 0.265 | <= 0.25 |
| Transaction cost survival (10bps/trade, 212 trades) | PASS | net Sharpe 0.859 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass fraction | >= 0.75 |
| Parameter sensitivity | PASS | rel_std 0.133 | <= 0.5 |

## Decision: REJECT

Max drawdown (26.5%) narrowly exceeds the 25% threshold. All other 4
validators pass cleanly (Sharpe just above 1.0, near-perfect walk-forward,
low parameter sensitivity, cost-survival intact). This is a genuine
near-miss driven by drawdown risk, not by weak edge -- a future iteration
could revisit with an added stop-loss or volatility-regime gate (this
strategy already shows the edge decays sharply in the high-vol tercile:
2/12 pass vs 8/12 in low-vol) to control drawdown without killing the edge.

Tried `max_hold_days=7` as an alternative (tighter time-stop) hoping to cut
drawdown -- it made MDD worse (0.297) and lowered net Sharpe after costs
(0.777), so the max_hold_days=10 config remains the better (still rejected)
option.
