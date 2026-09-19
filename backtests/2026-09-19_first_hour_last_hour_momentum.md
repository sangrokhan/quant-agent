# First-Hour/Last-Hour Intraday Momentum (Gao, Han, Li & Zhou 2017) — REJECTED (near-miss)

**Hypothesis:** Per Gao, Han, Li & Zhou (2017) "Market Intraday Momentum"
(recreated by QuantConnect's "Intraday ETF Momentum" tutorial,
https://www.quantconnect.com/research/15348/intraday-etf-momentum/), the
sign of an ETF's first half-hour return predicts the sign of its last
half-hour return. Adapted to 1-hour bars (data/loaders.py's yfinance
interval="1h" covers ~2yr of history vs. interval="30m"'s ~60-day cap):
long the last hour if the first hour's return is positive (above
`threshold`), short if negative, flat otherwise. First strategy in this
repo to trade an intraday first/last-hour sign-prediction mechanism
(distinct from the existing Chande Intraday Momentum Index oscillator,
2026-09-05-071/2026-09-14-100, which is an unrelated open-to-close-body
RSI-analog).

## Step 6 — Grid test summary

Grid: `threshold` in {0.0, 0.001, 0.002}, symbols equity={SPY,IWM}
crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3, ~700-day lookback window
(constrained by yfinance's 1h-interval history limit). 36 total cells.

- `pass_fraction`: 8/36 = **0.222** (notably higher than the prior two
  rejected iterations this trigger, and passes broadly across BOTH asset
  classes and ALL THREE vol regimes, not just a narrow low-vol slice)
- `by_asset_class`: equity 5/18 passed, crypto 3/18 passed
- `by_vol_regime`: low 5/12, mid 2/12, high 1/12
- `best_cell`: IWM, threshold=0.0, low-vol regime, Sharpe=4.55
- `worst_cell`: IWM, threshold=0.002, high-vol regime, Sharpe=-2.85

## Step 7 — Single-config validation (best cell: IWM, threshold=0.0,
~700-day full sample)

| Validator | Result | Value | Threshold | Pass |
|---|---|---|---|---|
| Sharpe ratio | full-sample | 0.859 | >= 1.0 | **FAIL** (close, but below) |
| Max drawdown | full-sample | 0.065 | <= 0.25 | pass |
| Tx-cost survival (5bps/trade, 475 trades) | net Sharpe | -0.665 | >= 0.5 | **FAIL** |
| Walk-forward (manual 4-split) | pass_fraction | 0.75 | >= 0.75 | pass |
| Parameter sensitivity (3-cell threshold sweep) | relative_std | 0.418 | <= 0.5 | pass |

Unlike the prior two rejected iterations this trigger, this is a genuine
near-miss: 3 of 5 validators pass (max drawdown, walk-forward, parameter
sensitivity), and full-sample Sharpe (0.86) is close to (not wildly off
from) the 1.0 threshold. The decisive failure is transaction costs: with
threshold=0.0 the strategy takes a position on almost every trading day
(475 active days out of ~479), so at 5bps/trade the cumulative cost drag
(23.75% over the sample) erases the edge entirely.

## Decision: REJECTED (near-miss, revisit with higher threshold /
different cost assumption)

Sharpe and tx-cost-survival fail; per this repo's accept criterion (all
validators must pass), this is a rejection. However, unlike the prior two
iterations' clean overfitting artifacts, this looks like a genuinely
promising signal with too much trading frequency for a 5bps/trade cost
assumption. **Recommended for a future loop to revisit**: (a) raise
`threshold` well above 0.002 to trade far less often (fewer, higher-
conviction signals should reduce the tx-cost drag proportionally more
than the edge), or (b) test with a more realistic intraday cost
assumption (ETFs like SPY/IWM typically have <1bps effective spread cost
for liquid names, vs the flat 5bps/trade default used here which may be
calibrated for daily-bar strategies with far fewer trades). Strategy file
kept in `strategies/` as a record (not live) but flagged in notes as a
near-miss worth revisiting, not a dead end.
