# 2026-09-09 — Bitcoin Regime Signal for Growth Equities (rejected)

**Hypothesis** (id `2026-09-09-114`): Per QuantConnect Research Publication
"Bitcoin Regime Signal for Growth Equities"
(https://www.quantconnect.com/research/21195/bitcoin-regime-signal-for-growth-equities/):
hold QQQ only while Bitcoin trades above its 50-day SMA AND has positive
20-day rate of change (both conditions, AND-gate); otherwise flee to
cash/short-duration bonds. Source's own rationale: BTC trades 24/7 with a
heavily leveraged derivatives market that reacts to risk-appetite shifts
faster than equities (Iyer 2022: BTC spillovers explain ~14-18% of equity
volatility variation since 2020). Source's own reported backtest (Jan
2014-Aug 2026, Bitfinex BTCUSD, **weekly rebalance**): strategy Sharpe 0.838
vs SPY buy-hold 0.564 and QQQ buy-hold 0.682; 25/25 parameter combos beat
SPY, 23/25 beat QQQ in a moving-average x ROC sensitivity sweep. Novel
indicator/technique combo in this repo: using BTC's own price action as an
EXTERNAL regime gate for QQQ/SPY (distinct from DXY/HYG-LQD/yield-curve
macro-proxy gates already tested, which use FX/credit/rates rather than
crypto).

Strategy file: `strategies/2026-09-09_btc_regime_signal_equities.py`

**Implementation deviation from source**: this repo's grid/validator
framework operates on daily bars throughout, so the regime gate is evaluated
**every day** here rather than the source's own weekly-only rebalance. This
is a stricter/noisier test of the same underlying signal, not a different
hypothesis, but it directly causes much higher trade frequency (see below).

## Step 6 grid summary (sma_window ∈ {30,50,70} × roc_window ∈ {10,20,30} × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles, 108 cells)

- `pass_fraction`: 0.287 (31/108) — **best pass_fraction of this cron
  trigger's 4 candidates**
- `by_asset_class`: equity 31/54, crypto 0/54 (BTC/ETH themselves fail
  entirely as the traded asset — expected, since the signal source and
  traded asset are the same series there, degenerate)
- `by_vol_regime`: low 17/36, mid 1/36, high 13/36 — notably passes in BOTH
  low AND high vol regimes (unlike every other candidate tested this
  trigger, which passed almost exclusively in low-vol slices only) —
  consistent with the source's own framing as a risk-off protection
  mechanism specifically valuable during turbulent (high-vol) periods
- `best_cell`: sma_window=50, roc_window=20 (source's own default config),
  QQQ, low-vol regime, Sharpe 1.70

## Single-config validators (source's default config: sma_window=50, roc_window=20), full 2019-2026 sample, DAILY evaluation

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.732 ❌ | 0.737 ❌ | ≥ 1.0 |
| Max drawdown | 0.272 ❌ | 0.195 ✅ | ≤ 0.25 |
| TC survival (10bps/trade) | **-0.101** ❌ | **-0.156** ❌ | ≥ 0.5 net Sharpe |
| Parameter sensitivity (sma_window 30/50/70 sweep, both symbols) | 0.156 ✅ | | ≤ 0.5 relative std |
| Trades | 952 | 952 | — |

## Verdict: **reject** (both QQQ and SPY)

Full-sample Sharpe fails both symbols and TC-survival fails catastrophically
(net Sharpe goes decisively negative after a modest 10bps/trade cost) — **952
trades over the 2019-2026 sample is roughly 2.7 trades/week**, an order of
magnitude more churn than the source's own weekly-rebalance design, which
this daily-evaluation adaptation directly causes (the BTC regime gate flips
frequently on a daily cadence even though the underlying signal is
economically a weekly-scale regime read). Parameter sensitivity is clean
(0.156, well under the 0.5 threshold) and the grid's by_vol_regime breadth
(passing in both low AND high vol, unlike every other candidate this
trigger) is a genuinely distinctive and encouraging signature consistent
with the source's own framing. **This strategy is a strong candidate for a
follow-up iteration that implements a proper weekly-rebalance version**
(evaluate/trade the regime gate only once per week, matching the source's
own methodology exactly, rather than daily) — the TC-survival failure looks
like an artifact of the evaluation-frequency mismatch, not a fundamental
flaw in the underlying signal.
