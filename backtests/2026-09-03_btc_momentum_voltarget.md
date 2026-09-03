# Backtest Report — 2026-09-03_btc_momentum_voltarget

**Hypothesis:** BTC/USDT absolute momentum (45-day lookback, shorter than
the prior 90-day attempt) combined with an inverse-volatility position-size
overlay (target 40% annualized vol, size = min(1, target_vol/realized_vol),
never levered above 1x) can retain the Sharpe edge seen in
2026-09-03-002's parameter sweep while cutting max drawdown into budget by
de-risking during high-realized-vol stretches instead of using a binary
in/out position.

**Universe / period:** BTC/USDT, daily bars, 2019-01-01 to 2026-09-01
(source: `data/loaders.py::load_crypto`, ccxt/binance, cache-first).

**Signal:** long-direction when `close[t]/close[t-45]-1 > 0`; position size
= `min(1, 0.40 / realized_20d_annualized_vol)`; flat otherwise. No shorting.
Position lagged by 1 day to avoid look-ahead.

## Results

| Validator | Result | Value | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio (annualized, freq=D) | 1.237 | >= 1.0 | ✅ pass |
| Max drawdown | 47.6% | <= 35% | ❌ FAIL |
| Transaction cost survival (10bps/trade, 1231 "trades") | net Sharpe 0.42 | >= 0.5 | ❌ FAIL |
| Parameter sensitivity (lookback ∈ {30,45,60,90}d, Sharpe) | rel.std 0.129 | <= 0.5 | ✅ pass |
| Walk-forward | not run | — | ⚠️ SKIPPED (known scaffold bug, see 2026-09-03-002 notes: `vbt.utils.splitting` missing in installed vectorbt) |

Per-lookback MDD (all still exceed 35% budget): 30d=39.3%, 45d=47.6%,
60d=52.2%, 90d=48.4%. Days in market: 1560/2801 (~55.7%).

## Interpretation

The vol-targeting overlay improved Sharpe meaningfully (0.92 → 1.24 at
comparable lookback territory, now clearing the 1.0 bar) and reduced max
drawdown relative to the pure binary-position 90-day momentum strategy
(66.0% → 47.6% at 45d, or 39.3% at the best lookback of 30d) — directional
progress in the intended direction, but **not enough**: even the best
per-lookback MDD (39.3% at 30d) still exceeds the 35% hard budget, let alone
the tighter 25% budget used elsewhere in this repo. The de-risking is being
triggered by *realized* vol looking backward 20 days, which lags fast BTC
crashes (e.g. sharp single-week drawdowns) — by the time the vol-target
overlay recognizes elevated vol and cuts size, a meaningful chunk of the
drawdown has often already happened.

Additionally, transaction-cost-survival failed this run: the continuous
[0,1] position sizing changes size on essentially every day realized vol
moves (not just on momentum sign flips), which the current
`check_transaction_cost_survival` implementation (a flat count of days
where position changed at all) counts as ~1231 "trades" over 2801 days —
this is an artifact of comparing a continuous-sizing strategy against a
transaction-cost check designed for discrete {0,1} strategies, not
necessarily a realistic cost estimate (a real implementation would round
position changes to a minimum rebalance threshold, e.g. only rebalance if
size changes by >10 percentage points). Flagged as a validator/strategy
interface mismatch for a future loop rather than a fundamental flaw in the
edge itself, but it fails the check as run, so it's recorded as a fail.

## Decision: REJECT

Max drawdown fails the hard risk gate at every lookback tested (best case
39.3% vs 35% budget), and transaction-cost-survival also fails (though
partly a validator/strategy granularity mismatch, see above). Sharpe and
parameter-sensitivity both passed, showing the underlying momentum +
vol-scaling idea has a real edge signal, but the risk-adjusted downside
control is still insufficient to accept under this repo's thresholds.

## Notes for future loops

- Vol-targeting with a 20-day *realized* (backward-looking) vol window
  reacts too slowly to sudden BTC crashes. A future loop could try a
  shorter/faster vol estimator (e.g. EWMA with a short half-life, or
  intraday-range-based vol) to react faster, or add a hard stop-loss
  circuit breaker on top of the continuous sizing (binary risk-off if
  drawdown-from-peak exceeds e.g. 15%, independent of the vol estimate).
- The transaction-cost-survival validator (`validation/validators.py`)
  assumes a strategy trades on discrete position changes; it doesn't handle
  continuous position-sizing strategies well (every daily vol wiggle counts
  as a full "trade"). Worth adding a `min_rebalance_threshold` parameter to
  either the validator or to strategies using continuous sizing, so trade
  counts reflect realistic rebalancing frequency rather than daily noise.
- Walk-forward validator is still broken (`vbt.utils.splitting` missing) —
  carried over from 2026-09-03-002, still unfixed, still blocking a useful
  robustness check for trend-following strategies specifically (which are
  the family most prone to regime-dependence, per 2026-09-01-001's original
  walk-forward failure).
