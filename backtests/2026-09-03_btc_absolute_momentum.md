# Backtest Report — 2026-09-03_btc_absolute_momentum

**Hypothesis:** BTC/USDT exhibits positive absolute (time-series) momentum:
when trailing 90-day return is positive, staying long captures continued
upside; when negative, staying flat avoids further downside. Rationale:
crypto markets are dominated by momentum-chasing retail flow and slower
information diffusion than equities, so established trends should persist.

**Universe / period:** BTC/USDT, daily bars, 2019-01-01 to 2026-09-01
(source: `data/loaders.py::load_crypto`, ccxt/binance, cache-first).

**Signal:** long when `close[t] / close[t-90] - 1 > 0`; flat otherwise. No
shorting. Position lagged by 1 day to avoid look-ahead.

## Results

| Validator | Result | Value | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio (annualized, freq=D) | 0.92 | >= 1.0 | ❌ FAIL |
| Max drawdown | 66.0% | <= 25% (35% also tried) | ❌ FAIL |
| Transaction cost survival (10bps/trade, 89 trades) | 0.89 | >= 0.5 | ✅ pass |
| Walk-forward | not run | — | ⚠️ SKIPPED (see Notes — library API bug) |
| Parameter sensitivity (lookback ∈ {30,60,90,120,150}d) | rel.std 0.22 | <= 0.5 | ✅ pass |

Trade count: 89 position changes over ~7.7 years. Days in market: 1555 /
2801 (~55.5%). Full parameter grid (Sharpe by lookback): 30d=1.33, 60d=1.25,
90d=0.92, 120d=1.04, 150d=0.69.

## Interpretation

Mixed but net-negative result. The parameter sensitivity check passed
(shorter lookbacks like 30-60d even clear the Sharpe >= 1.0 bar), and
transaction costs are easily survivable given the modest trade count. But
at the pre-registered 90-day lookback the strategy **fails both the Sharpe
threshold (0.92 vs 1.0) and, more decisively, max drawdown (66% vs the 25%
budget — even a looser 35% budget would still fail)**. A 66% drawdown is in
line with simply holding BTC through 2021→2022 and 2024→2025 cycles while
occasionally getting whipsawed out near local tops/bottoms; the momentum
filter did not meaningfully de-risk the exposure relative to buy-and-hold.
Since max drawdown is a hard risk-management gate (not just a headline
return metric), this is rejected regardless of the Sharpe being close to
threshold.

## Decision: REJECT

Failed max_drawdown decisively (66% vs 25-35% budget) and Sharpe narrowly
(0.92 vs 1.0) at the pre-registered parameter. Walk-forward not run (see
below) but would not change the outcome — a strategy that already fails a
hard risk gate at its designated parameterization doesn't get promoted on
the basis of an as-yet-unrun robustness check.

## Notes for future loops

- **Scaffold bug found:** `validation/validators.py::check_walk_forward`
  calls `vbt.utils.splitting.RangeSplitter(...)`, but the installed
  vectorbt version does not expose `vbt.utils.splitting` (raises
  `AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`).
  Not fixed this loop since the MDD failure alone was decisive and workload
  didn't require walk-forward to reach a conclusion, but this will block
  walk-forward validation for *any* future strategy until fixed — worth a
  dedicated loop to patch (likely needs vectorbt's newer
  `vbt.Splitter`/`vbt.RangeSplitter` top-level API depending on installed
  version, per vectorbt's migration between generations of the splitting
  API).
- The parameter sweep suggests shorter lookbacks (30-60d) have better
  raw Sharpe than 90d, but drawdown was not re-checked per-lookback here —
  a future loop revisiting this idea should sweep MDD (not just Sharpe)
  across the parameter grid, and consider adding a hard-stop/vol-targeting
  overlay (e.g. reduce position size in high realized-vol regimes, similar
  in spirit to 2026-09-03-001's regime filter but applied to a trend
  strategy instead of mean-reversion) specifically to attack the drawdown
  problem rather than abandoning momentum entirely.
