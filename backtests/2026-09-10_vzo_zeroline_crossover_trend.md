# Volume Zone Oscillator (VZO) zero-line crossover, trend-gated

**Hypothesis source:** SERP synthesis of thinkorswim's VolumeZoneOscillator
study description and Investopedia/TradingView VZO zone semantics
(VZO>5% = positive-trend zone, VZO<-5% = negative-trend zone, +/-40% =
extreme overbought/oversold). Standard VZO formula already known from this
repo's 2026-09-04-122 entry: VZO=100*(VP/TV), VP=EMA of signed OBV-style
volume, TV=EMA of raw volume. This iteration tests the ZERO-LINE CROSSOVER
technique (long when VZO crosses from <=0 to >0, gated by close>SMA(trend_window)),
distinct from 2026-09-04-122's "-40% oversold recovery" mean-reversion
technique on the same oscillator.

## Grid test (Step 6)

`param_grid={"vzo_span": [10,14,20], "trend_window": [50,100]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 14/72 = 0.194**
- By asset class: equity 14/36 (0.39), crypto 0/36 (0.0) — decisive crypto rejection
- By vol regime: low 12/24, mid 2/24, high 0/24 — narrow low-vol-only edge
- Best cell: QQQ, low-vol, vzo_span=20/trend_window=50, Sharpe 3.09
- Worst cell: QQQ, high-vol, vzo_span=20/trend_window=50, Sharpe -1.16

## Full-sample validator suite (Step 7), config vzo_span=20/trend_window=50

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.601 ❌ | 0.571 ❌ |
| Max drawdown (<=0.25) | 0.236 ✅ | 0.189 ✅ |
| Tx-cost survival (net Sharpe >=0.5, 10bps/trade) | 0.382 ❌ | 0.284 ❌ |
| Walk-forward (manual 4-slice fallback) | 0.50 ❌ (2/4) | 0.50 ❌ (2/4) |
| Parameter sensitivity (relative std <=0.5) | 0.083 ✅ | 0.225 ✅ |

QQQ: 99 trades. SPY: 118 trades. Both fail 3 of 5 validators decisively
(Sharpe, transaction-cost survival, walk-forward).

## Decision

**Reject** for both QQQ and SPY (each fails Sharpe, TC-survival, and
walk-forward). Crypto rejected decisively (0/36 grid cells). The grid's
strong low-vol-regime performance (12/24 pass, best cell Sharpe 3.09) is
a narrow-slice artifact — the full-sample validator suite shows the
strategy does not hold up unconditionally across the whole 7.7-year
sample once mid/high-vol periods are included. Frequent zero-line
crossings (~100+ trades over the period) also make it more transaction-
cost sensitive than the oversold-recovery variant already accepted-nowhere
in this family.
