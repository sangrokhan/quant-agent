# Bullish Three-Bar Reversal (probe-bar low + confirmation close)

**Hypothesis:** Per https://www.luxalgo.com/library/concept/three-bar-reversal/,
a bullish three-bar reversal: bar1 continues a decline, bar2 makes the
sequence's lowest low (probe/pivot), bar3 closes above bar2's high
(confirmation). Entry on bar3 close, stop below bar2's low. First
bar-count (non-candlestick-anatomy) reversal strategy in this repo.

**Strategy file:** `strategies/2026-09-08_three_bar_reversal.py`

## Grid test (Step 6)

`param_grid={"trend_window": [10, 20, 30], "use_trend_filter": [True, False]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- 72 total cells, 15 passed (pass_fraction=0.208)
- By asset class: equity 15/36, crypto 0/36
- By vol regime: low 12/24, mid 3/24, high 0/24 -- concentrated in low-vol
  regime, same cherry-picking-risk pattern flagged in prior iterations
- Best cell: SPY, trend_window=10/use_trend_filter=False, low-vol regime, Sharpe 3.03
- Worst cell: SPY, trend_window=10/use_trend_filter=True, high-vol regime, Sharpe -0.29

## Single-config validators (Step 7) -- best config trend_window=10/use_trend_filter=False

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.461 FAIL | 0.785 FAIL | >= 1.0 |
| Max drawdown | 36.3% FAIL | 32.7% FAIL | <= 25% |
| TC-survival (10bps) | 0.344 FAIL | 0.690 PASS | >= 0.5 |
| Walk-forward (manual 4-split) | 3/4 positive, 0.75 PASS (marginal, one strongly negative split -0.784) | 3/4 positive, 0.75 PASS (marginal, one negative split -0.078) | >= 0.75 |
| Parameter sensitivity (trend_window relative std, no-filter variant) | ~0 PASS | ~0 PASS | <= 0.5 |

## Decision (Step 8)

**Reject.** Despite the eye-catching isolated best-cell Sharpe (3.03,
SPY low-vol regime with no trend filter), the full-sample Sharpe on BOTH
SPY (0.461) and QQQ (0.785) decisively fails the >=1.0 threshold, and both
also fail max-drawdown (36.3%/32.7%, both far over the 25% ceiling). This
matches the now-familiar pattern (also seen in 2026-09-08-111/112) where a
strong isolated low-vol-regime grid cell does not survive full-sample
validation. Crypto rejected decisively (0/36 grid cells).
