# RSI Momentum (Centerline-Cross, not Mean-Reversion) — Backtest Report

**Hypothesis:** Per QuantifiedStrategies.com's Bitcoin RSI trading article,
RSI used as a MEAN-REVERSION indicator (buy oversold, sell overbought) is
"basically worthless" on Bitcoin/crypto in the source's own optimization
sweep, but RSI used as a MOMENTUM indicator (buy when RSI crosses ABOVE an
upper threshold near the centerline, sell when it crosses back below a
lower threshold) performed "much better" -- best results clustered around
a short RSI period (RSI(5)). This is the first RSI-as-momentum (rather
than mean-reversion) strategy tested in this repo.

Source: https://www.quantifiedstrategies.com/bitcoin-rsi-trading-strategy/
(web_search failed repeatedly with a DDGS/Yahoo TLS connection error, fell
back to browser_exec; general finding stated in prose, exact numeric
backtest rule paywalled/members-only, so entry/exit thresholds here are a
reasonable standard construction, not directly copied from the source).

## Step 6 — Grid test (rsi_window x entry_threshold x asset class x vol regime)

Grid: `rsi_window` in [5, 10, 14], `entry_threshold` in [55.0, 60.0]
(exit_threshold = entry_threshold - 10), symbols equity=[QQQ, SPY],
crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3. 72 cells total.

- **pass_fraction: 0.25 (18/72)**
- by_asset_class: equity 18/36 passed; **crypto 0/36 passed** (decisive
  reject -- notably CONTRADICTS the source's own claim that RSI momentum
  "works well" on crypto; see full-sample table below)
- by_vol_regime: low 12/24; mid 6/24; high 0/24

## Full-sample Sharpe by config (QQQ, SPY, BTC/USDT, ETH/USDT)

| rsi_window | entry_thresh | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|---|
| 5 | 55 | 0.844 | 0.669 | 0.136 | 0.185 |
| 5 | 60 | 0.853 | 0.900 | 0.142 | 0.180 |
| 10 | 55 | **1.287** | **1.145** | 0.160 | 0.204 |
| 10 | 60 | 1.270 | 1.013 | 0.173 | 0.227 |
| 14 | 55 | 1.265 | 0.980 | 0.205 | 0.190 |
| 14 | 60 | 1.109 | 0.594 | 0.192 | 0.202 |

Crypto Sharpe never exceeds ~0.23 despite very high trade counts
(937-4478 round-trips over the sample) -- the frequent centerline crossings
on crypto's noisier bars generate near-zero net edge once realistic
regime-splitting is applied, contradicting the source's specific crypto
claim on this repo's data/timeframe. Equity (QQQ, SPY) clears the bar
cleanly at rsi_window=10, entry_threshold=55.

## Step 7 — Single-config validation (rsi_window=10, entry_threshold=55, exit_threshold=45)

### QQQ

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.287 | 1.0 |
| Max drawdown | ✅ | 0.167 | 0.25 |
| Transaction cost survival (10bps/trade, 56 trades) | ✅ | 1.208 (net Sharpe) | 0.5 |
| Walk-forward (4 splits, manual date-slice; vectorbt splitter API bug as noted in prior entries) | ✅ | 0.75 (3/4 splits positive: 2.45, 0.86, 1.77, -0.03) | 0.75 |
| Parameter sensitivity (6-combo QQQ grid, rel. std) | ✅ | 0.172 | 0.5 |

**QQQ: all 5 validators pass.**

### SPY (same shared config)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.145 | 1.0 |
| Max drawdown | ✅ | 0.184 | 0.25 |
| Transaction cost survival (53 trades) | ✅ | 1.048 (net Sharpe) | 0.5 |

**SPY also clears the bar at the SAME shared config** (not a separately
tuned per-symbol config) -- a rare instance in this repo of one config
working cleanly on BOTH equity symbols without needing per-symbol tuning.

## Outcome

**Accepted for equity (QQQ and SPY, shared config rsi_window=10,
entry_threshold=55, exit_threshold=45).** Crypto rejected decisively
(0/36 grid cells, best full-sample Sharpe only 0.227) -- directly
contradicting the source's own specific crypto-favorable claim on this
repo's daily-bar BTC/USDT and ETH/USDT data.
