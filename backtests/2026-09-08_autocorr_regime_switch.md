# Adaptive Momentum/Mean-Reversion via Rolling Lag-1 Autocorrelation

**Hypothesis:** Per https://blog.quantinsti.com/autocorrelation/, positive
lag-1 return autocorrelation implies exploitable momentum, negative implies
mean-reversion. This strategy computes rolling 40/60-day lag-1
autocorrelation of daily returns and switches logic: momentum regime
(ACF>threshold) trades trend continuation, mean-reversion regime
(ACF<-threshold) buys 1-day dips with a short hold. First autocorrelation-
regime-adaptive strategy in this repo.

**Strategy file:** `strategies/2026-09-08_autocorr_regime_switch.py`

## Grid test (Step 6)

`param_grid={"acf_window": [40, 60], "acf_threshold": [0.05, 0.1, 0.15]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- 72 total cells, 15 passed (pass_fraction=0.208)
- By asset class: equity 15/36; crypto 0/36 (decisive fail)
- By vol regime: low 8/24, mid 6/24, high 1/24 -- reasonably spread across
  low/mid this time (less concentrated than prior iterations' patterns)
- Best cell: QQQ, acf_window=40/acf_threshold=0.05, low-vol regime, Sharpe 2.29
- Worst cell: ETH/USDT, acf_window=60/acf_threshold=0.15, mid-vol, Sharpe -0.05

## Single-config validators (Step 7) -- config acf_window=40/acf_threshold=0.05

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.360 PASS | 0.915 FAIL | >= 1.0 |
| Max drawdown | 28.2% FAIL | 31.3% FAIL | <= 25% |
| TC-survival (10bps, 254/251 trades) | 0.959 PASS | 0.508 PASS | >= 0.5 |
| Walk-forward (manual 4-split) | 4/4 positive, 1.0 PASS | 4/4 positive, 1.0 PASS | >= 0.75 |
| Parameter sensitivity (acf_threshold 0.05/0.1/0.15 relative std) | 0.372 PASS | 0.405 PASS | <= 0.5 |

## Decision (Step 8)

**Reject.** Despite a decent grid pass_fraction (0.208) and QQQ's full-
sample Sharpe passing (1.360), BOTH QQQ (28.2%) and SPY (31.3%) fail the
max-drawdown threshold (<=25%) -- the strategy trades very frequently
(~250 trades over 7.7yr, roughly weekly) and evidently accumulates large
drawdowns during regime-transition whipsaws even though average Sharpe
looks acceptable. Since not all validators pass for either symbol (QQQ
fails MDD, SPY fails both Sharpe and MDD), this does not meet the Step 8
accept bar. Crypto rejected decisively (0/36 grid cells).
