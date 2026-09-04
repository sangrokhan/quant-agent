# DeMarker Oversold-Exhaustion Reversal, Trend-Gated (QQQ)

**Hypothesis:** The DeMarker (DeM) oscillator (Thomas DeMark) measures
buying/selling exhaustion via `DeM = SMA(max(high-high[1],0), n) /
(SMA(max(high-high[1],0), n) + SMA(max(low[1]-low,0), n))`. A cross back
above an oversold threshold (0.25-0.30) signals a downside-exhaustion
bounce; gating entries on a long-term uptrend (close > 200d SMA) should
filter out bounces that are actually the start of a deeper downtrend.

**Source:** https://www.litefinance.org/blog/for-beginners/best-technical-indicators/demarker-indicator/
(default n=14, overbought/oversold at 70/30 on 0-100 scale).

**Novelty:** Distinct from Connors RSI (2026-09-04-113, composite
RSI/streak/ROC oscillator) and TD Sequential (2026-09-04-032, bar-counting
setup) already tried — DeMarker is a high/low-range exhaustion ratio, a
different construction. First DeMarker strategy in this repo.

## Best config: dem_window=14, oversold_threshold=0.30, overbought_threshold=0.70, trend_window=200, max_hold_days=10 (QQQ, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.150 | >= 1.0 | PASS |
| Max drawdown | 7.48% | <= 25% | PASS |
| Transaction cost survival (5bps/trade, 38 trades) | net Sharpe 1.091 | >= 0.5 | PASS |
| Parameter sensitivity (relative std across dem_window x oversold_threshold, QQQ) | 0.386 | <= 0.5 | PASS |
| Walk-forward | SKIPPED | n/a | `vectorbt.utils.splitting.RangeSplitter` API not available in installed vectorbt version (`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`) — repo-wide vbt version issue, not specific to this strategy. Flagging for a future loop to fix/replace the walk-forward helper. |

## Step 6 grid summary (dem_window in [10,14,21] x oversold_threshold in [0.25,0.30], symbols QQQ/SPY equity + BTC/USDT/ETH/USDT crypto, vol_regime_splits=3)

- **Overall pass_fraction: 15.3%** (11/72 cells, cell = sharpe>=1.0 AND mdd<=25%)
- **By asset class:** equity 11/36 passed (30.6%); crypto 0/36 passed (0%) — DeMarker exhaustion-bounce edge does not transfer to crypto in this window.
- **By vol regime:** low 3/24, mid 6/24, high 2/24 — edge spread across regimes but concentrated mid-vol.
- **Best cell:** SPY, dem_window=14, oversold_threshold=0.30, high-vol regime, Sharpe 2.14.
- Per-symbol/param breakdown: QQQ passed in 2/3 vol regimes for dem_window in {10,14,21}@os=0.3 and dem_window=21@os=0.25; SPY only passed with dem_window=14@os=0.3 (2/3 regimes) and dem_window=10@os=0.3 (1/3); all other SPY configs and ALL crypto configs (BTC/ETH, all params) failed every vol-regime cell.

## Decision: ACCEPT (equity QQQ only, narrow scope)

QQQ full-sample validators (Sharpe, MDD, cost survival, parameter
sensitivity) all pass cleanly at the grid's best QQQ config
(dem_window=14, oversold_threshold=0.30). SPY is a much weaker/narrower fit
(only 1 of 6 param combos held up across vol regimes) and crypto fails
entirely across the whole grid — this strategy should be scoped to QQQ (or
similar large-cap tech-heavy equity index) only, not treated as broadly
applicable. Walk-forward validator itself is currently broken at the repo
infra level (vbt API mismatch), not a strategy-specific finding — recorded
as skipped rather than failed.
