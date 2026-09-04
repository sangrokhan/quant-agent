# Backtest Report: Woodie's CCI Zero Line Reject (2026-09-05)

**Hypothesis:** Woodie's CCI trading system's signature "Zero Line Reject"
(ZLR) pattern: during an established trend (CCI staying on one side of
zero for several consecutive bars), CCI dips toward the zero line but
bounces back without actually crossing it, signaling trend-continuation
worth a pullback entry. Per TrendSpider's aggregated Woodie's CCI guide,
ZLR is described as "the workhorse trade... a momentum pullback entry: it
buys resumption of an established trend rather than picking tops or
bottoms." Tested here as: CCI dips into a (0, reject_band] tolerance zone
after an established positive-CCI trend, then bounces back above
reject_band — entering long on that bounce. Exit when CCI crosses below
zero (trend genuinely broken) or a max-hold time-stop.

**Source:** https://trendspider.com/learning-center/woodies-cci-a-comprehensive-guide/
(aggregated Woodie's CCI system description, ZLR pattern definition).

**Novelty:** distinct from both already-tested CCI strategies in this repo
— the oversold-mean-reversion CCI<-90 dip-buy (2026-09-04-024, opposite
economic thesis: buying deep oversold rather than a shallow pullback within
an existing uptrend) and the CCI>+100 breakout-momentum entry
(2026-09-04-072, requires a fresh +100 cross rather than staying positive
and dipping toward zero).

## Grid test (validation/grid_test.py)

- param_grid: `cci_window` in {14, 20}, `trend_established_bars` in {6, 10},
  `reject_band` in {20, 30}, `max_hold_days` fixed at 15
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits = 3
- total_cells = 96, passed_cells = 17, **pass_fraction = 17.7%**
- by_asset_class: equity 17/48, crypto 0/48
- by_vol_regime: low 15/32, mid 0/32, high 2/32
- best_cell: QQQ, cci_window=20, trend_established_bars=10, reject_band=20,
  low-vol regime, Sharpe 2.17
- Best-looking config (cci_window=14, trend_established_bars=6,
  reject_band=30): QQQ 2/3 passed (avg Sharpe 1.18), SPY 1/3 passed (avg
  Sharpe 0.37), BTC/USDT 0/3 (avg Sharpe 0.13), ETH/USDT 0/3 (avg Sharpe
  0.02). **However**, `cci_window=20` configs collapse to near-zero Sharpe
  across the board (e.g. QQQ avg Sharpe -0.04 to 0.26) — a stark
  discontinuity vs `cci_window=14`, flagging high parameter sensitivity
  before even running the formal check.

## Single-config validators (config: cci_window=14,
trend_established_bars=6, reject_band=30, max_hold_days=15, full
2019-01-01..2026-09-01 sample)

| Symbol | Sharpe | MDD | TC-survival (10bps, N trades) | Passed all? |
|---|---|---|---|---|
| QQQ | 1.169 (PASS >=1.0) | 0.055 (PASS <=0.25) | 1.103 net Sharpe, 24 trades (PASS >=0.5) | numerically YES, but very thin trade count |
| SPY | 0.420 (FAIL <1.0, decisive) | 0.078 (PASS <=0.25) | 0.342 net Sharpe, 20 trades (FAIL <0.5) | NO |

Parameter sensitivity (QQQ, full 8-cell grid across cci_window/
trend_established_bars/reject_band, Sharpes ranging -0.04 to 1.18):
relative_std **0.921 vs 0.5 threshold — FAIL, decisively**. The QQQ Sharpe
collapses from ~1.1-1.2 at cci_window=14 to near-zero or negative at
cci_window=20, meaning the edge is entirely an artifact of one narrow
parameter choice, not a robust signal.

Walk-forward: skipped (known repo issue).

## Decision: REJECTED (decisive — parameter sensitivity failure; SPY also
decisive Sharpe miss)

QQQ numerically clears Sharpe/MDD/TC at the single nominal config, but only
on a thin sample (24 trades over 7.5 years) and the parameter-sensitivity
check shows this result does not generalize even to a modestly different
`cci_window` — a strong sign of overfitting to one specific setting rather
than a genuine ZLR edge. Combined with SPY's decisive Sharpe/TC failure and
crypto's complete failure (0/48), this is rejected rather than accepted on
a narrow QQQ-only scope, since even that QQQ result itself fails the
parameter-robustness bar.
