# Backtest Report: N-bar New High + Low IBS Breakout (2026-09-26)

## Hypothesis
Source: QuantifiedStrategies.com's "Buy When S&P 500 Makes New Intraday High"
(reproduced/tested at
https://www.prorealcode.com/topic/buy-when-sp500-makes-new-high-and-ibs-is-low-strategy/,
browser_exec, free/fully disclosed rule -- original QS article URL 404's but
its exact rules are quoted verbatim by the forum author who reproduced and
extended the backtest).

Rule: long entry when today's HIGH exceeds the highest high of the prior
`lookback_p-1` bars (a new short-term high) AND today's Internal Bar
Strength `IBS = (close-low)/(high-low)` is below `ibs_threshold` (bar closed
weak relative to its own range -- an intrabar pullback within an otherwise
strong/breaking-out bar). Exit when close > prior day's high (source's own
rule), or a `max_hold_days` safety time-stop (source has none; added here).

Distinct from every other IBS strategy in this repo: this is the first to
combine IBS with an N-bar-HIGH BREAKOUT trigger (buying strength+intrabar
weakness together) rather than using IBS alone/with a trend or oscillator
filter as a pure mean-reversion signal.

## Grid test summary (Step 6)

`lookback_p in {2,5,10} x ibs_threshold in {0.15,0.20,0.25}`, QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2016-01-01 to 2026-09-01:

- `pass_fraction = 0.343` (37/108)
- `by_asset_class`: equity 37/54, crypto 0/54
- `by_vol_regime`: low 11/36, mid 9/36, high 17/36
- `best_cell`: lookback_p=10, ibs_threshold=0.15, SPY, high-vol, Sharpe 1.598
- `worst_cell`: lookback_p=10, ibs_threshold=0.20, BTC/USDT, mid-vol, Sharpe -0.564

Full local 9-combo full-sample sweep (no vol slicing):
- QQQ: Sharpe ranges 0.821 (p=5,ibs=0.20) to 1.230 (p=2,ibs=0.15)
- SPY: Sharpe ranges 0.960 (p=5,ibs=0.25) to 1.413 (p=2,ibs=0.15)
- BTC/USDT: -0.114 to 0.681 (never clears 1.0)
- ETH/USDT: 0.154 to 0.525 (never clears 1.0)

Crypto decisively fails on the full grid; equity is consistently strong
across the entire local parameter neighborhood (unusually low sensitivity
for this repo).

## Single-config validation (Step 7)

Config: `lookback_p=2, ibs_threshold=0.15, max_hold_days=15` (best full-sample
cell, also near the source's own author-preferred region).

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.230 (pass) | 1.413 (pass) | >= 1.0 |
| Max drawdown | 0.131 (pass) | 0.120 (pass) | <= 0.25 |
| TC survival (net Sharpe, 5bps/trade) | 1.118 (pass) | 1.233 (pass) | >= 0.5 |
| Walk-forward (4 splits) | 1.00 (pass) | 1.00 (pass) | >= 0.75 |
| Parameter sensitivity (rel. std, 9-cell local grid) | 0.133 (pass) | 0.122 (pass) | <= 0.5 |

Num trades: QQQ 123, SPY 136 (2016-2026, ~12-13/yr, reasonable turnover).

## Decision: ACCEPTED (QQQ and SPY both)

All validators pass for both equity symbols. Crypto (BTC/USDT, ETH/USDT)
decisively fails the grid (0/54 cells) and was not single-config validated
-- scope this strategy to equity only.

Source: https://www.prorealcode.com/topic/buy-when-sp500-makes-new-high-and-ibs-is-low-strategy/
(browser_exec; original QuantifiedStrategies.com article page 404's, exact
rules quoted verbatim by the forum thread author who also independently
backtested and parameter-swept it).
