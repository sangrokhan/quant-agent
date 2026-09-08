# Backtest Report: Overnight-Return Premium, Trend + VIX-Calm-Regime Gate

**Strategy file:** `strategies/2026-09-08_overnight_return_vix_calm_gate.py`
**Outcome:** REJECTED (transaction-cost survival fail)

## Hypothesis

Per Quantpedia "Market Sentiment and an Overnight Anomaly"
(https://quantpedia.com/strategies/market-sentiment-and-an-overnight-anomaly/,
source paper Vojtko/Hanicova, SSRN 3829582): hold SPY overnight only when
price > 20d SMA AND VIX < its own moving average (calm regime) AND a
proprietary sentiment indicator is bullish (source reports Sharpe 2.12,
MDD -10.97%, 2018-2021). We drop the unreplicable proprietary sentiment leg
and keep trend + VIX-calm gates, applied on top of the existing accepted
unconditional overnight-hold-trend-gate (2026-09-08-053). This directly
implements the OPPOSITE polarity suggested in 2026-09-07-020's own notes
(elevated-VIX gate rejected; try calm-VIX gate instead).

## Step 6 grid summary

Grid: `trend_window` in [50, 100] x `vix_window` in [10, 20, 40] x symbols
{QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto) x 3 vol-regime terciles
= 72 cells.

- **pass_fraction: 0.319** (23/72) -- notably better than the elevated-VIX
  gate's 0.185, and unlike that prior rejection, this one passes in ALL
  THREE vol regimes for the best config (trend_window=100, vix_window=10):
  QQQ low/mid/high Sharpe = 1.97 / 1.62 / 1.28, all passing (Sharpe>=1.0,
  MDD<=0.25).
- **by_asset_class:** equity 23/36, crypto 0/36 (decisive crypto reject, as
  expected -- no overnight session structure)
- **by_vol_regime:** low 12/24, mid 5/24, high 6/24 -- broader coverage than
  most rejected strategies this session, though still low-vol-skewed.
- **best_cell:** QQQ, trend_window=100, vix_window=40, low-vol, Sharpe=2.32

## Primary config (trend_window=100, vix_window=10 -- best cross-regime robustness)

| Validator | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe (full period) | 1.508 | 1.475 | >= 1.0 | PASS |
| Max Drawdown (full period) | 0.167 | 0.141 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade) | 0.374 (331 trades) | 0.172 (337 trades) | >= 0.5 | **FAIL** |
| Parameter sensitivity (QQQ, 6-combo grid, low-vol slice) | rel_std 0.082 | -- | <= 0.5 | PASS |
| Parameter sensitivity (QQQ, 6-combo grid, avg across regimes) | rel_std 0.161 | -- | <= 0.5 | PASS |
| Walk-forward | -- | -- | -- | SKIPPED (pre-existing `validators.py` vectorbt API mismatch, known repo-wide issue) |

## Decision: REJECTED

Sharpe and max drawdown both pass comfortably for both QQQ and SPY, and
parameter sensitivity is very robust (low relative_std). However,
**transaction-cost survival fails decisively for both symbols** (net Sharpe
0.37 QQQ / 0.17 SPY vs 0.5 threshold): the VIX-calm gate flips position far
more often (331-337 trades over 8.7yr) than the already-accepted plain
trend-gated overnight hold (2026-09-08-053, ~40 trades/8.7yr, which passed
transaction costs comfortably at net-Sharpe 1.37/1.32). The added VIX gate
raises gross Sharpe robustness across vol regimes but at a turnover cost
that erodes the edge once realistic per-trade costs are applied. Not
accepted; the existing 2026-09-08-053 remains the live overnight-hold
strategy in this repo. A future iteration could try a HYSTERESIS/smoothed
version of the VIX-calm condition (e.g. require N consecutive calm days
before flipping on, or vice versa) specifically to cut turnover while
keeping the cross-regime Sharpe improvement, if this angle is revisited.
