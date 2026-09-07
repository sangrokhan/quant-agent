# CCI Bullish Divergence

**Hypothesis:** Per https://www.avatrade.com/education/technical-analysis-indicators-strategies/cci-trading-strategies,
a bullish divergence (price makes a lower low while CCI makes a higher low)
signals a high-probability reversal, since divergence signals are rarer and
more reliable than simple threshold crosses. First CCI-divergence-specific
strategy in this repo (prior CCI strategies used only threshold/crossover
triggers).

**Strategy file:** `strategies/2026-09-08_cci_bullish_divergence.py`
(fixed a MAD-calculation bug during development: `raw=True` rolling apply
requires numpy ops, not pandas `.abs()`)

## Grid test (Step 6)

`param_grid={"cci_window": [14, 20], "pivot_window": [3, 5]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- 48 total cells, 5 passed (pass_fraction=0.104) -- decisive fail
- By asset class: equity 5/24, crypto 0/24
- By vol regime: low 0/16, mid 1/16, high 4/16
- Best cell: QQQ, cci_window=14/pivot_window=3, high-vol regime, Sharpe 1.67
- Worst cell: QQQ, cci_window=20/pivot_window=5, mid-vol regime, Sharpe -1.06

## Single-config validators (Step 7) -- best config cci_window=14/pivot_window=3

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | 0.734 FAIL | 0.579 FAIL |
| Max drawdown | 10.2% PASS | 5.9% PASS |
| TC-survival (10bps) | 0.696 PASS | 0.532 PASS |
| num_trades | 14 | 14 |

## Decision (Step 8)

**Reject.** Grid pass_fraction only 10.4% (5/48). The best cell's isolated
high-vol-regime Sharpe (1.67, QQQ) does not hold up full-sample: both QQQ
(0.734) and SPY (0.579) fail the >=1.0 Sharpe threshold, despite passing
MDD and TC-survival. Signal is also sparse (14 trades over 7.7yr on each
equity), consistent with divergence patterns being genuinely rare as the
source itself notes -- but rarity alone doesn't translate into a durable
edge here. Crypto rejected decisively (0/24 cells).
