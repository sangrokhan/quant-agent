# MACD-sign + WMA/EMA trend-position + Aroon crossover composite (Star, TASC May 2016) — Accepted (SPY only)

**Source:** https://traders.com/Documentation/FEEDbk_docs/2016/05/TradersTips.html
(Barbara Star, "Zero In On The MACD", TASC May 2016; TradeStation EasyLanguage
"PaintBar: Warning Symbols" code disclosed)

**Hypothesis:** Bullish continuation confirmed when three source-disclosed
independent signals align on the same bar: (1) MACD(12,26) positive,
(2) close above 34-WMA AND 55-EMA above 34-WMA (source's bullish warning
condition), (3) Aroon Up(25) crosses over Aroon Down(25) (source's own "A"
label condition). Exit: MACD turns non-positive, or max_hold_days time-stop.
The source presents these as independent discretionary chart overlays; this
iteration's own contribution is combining all three into one mechanical
entry trigger.

## Grid summary (72 cells: 2 aroon_length x 3 max_hold_days x 4 symbols x
3 vol regimes)

- pass_fraction: 0.1806 (13/72)
- by_asset_class: equity 8/36, crypto 5/36
- by_vol_regime: low 4/24, mid 7/24, high 2/24
- best config by avg-Sharpe-across-regimes: SPY, aroon_length=25,
  max_hold_days=10 — **3/3 vol-regime cells passed** (avg Sharpe 1.31)

## Single-config validation (SPY, aroon_length=25, max_hold_days=10)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.101 | >= 1.0 | PASS |
| Max drawdown | 4.7% | <= 25% | PASS |
| TC survival (net Sharpe, 8 trades) | 1.058 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 1.0 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (relative std) | 0.381 | <= 0.5 | PASS |

QQQ cross-check at the same config: Sharpe 0.618 (FAIL), MDD 5.6% (pass),
7 trades — does not generalize to QQQ.

## Verdict: ACCEPTED (SPY only)

All 5 validators pass for SPY at aroon_length=25/max_hold_days=10, with a
very low max drawdown (4.7%) and a fully-passing 4/4 walk-forward split.
**Caveat: extremely sparse signal** — only 8 trades over the full 2019-2026
sample — so while every validator formally passes, the sample size is small
and the strategy should be treated as a narrow, low-frequency SPY-specific
edge rather than a broadly robust system. Does NOT generalize to QQQ (Sharpe
0.618, fails) or to crypto (grid pass_fraction only 5/36, no single
BTC/ETH config passed all three vol regimes).
