# Standalone SMA(200) Trend-Following (price-position rule) — Backtest Report

**Hypothesis:** Per BoringEdge's Bitcoin Golden Cross backtest article, the
source's own comparison found the SIMPLER standalone 200-day SMA
price-position rule (long when close > SMA(200), flat otherwise, no second
MA required) beat the classic 50/200 golden-cross two-MA crossover on their
own BTC data. This repo has tested SMA(200) extensively as a GATING FILTER
alongside other signals but never as a standalone single-indicator
strategy. Testing the bare rule directly, long-only, no crossover mechanics.

Source: https://boringedge.com/bitcoin-golden-cross-strategy-backtest/
(fetched via browser_exec after web_search failed with a DDGS/TLS
connection error, fell back to Google search per RESEARCH_LOOP.md).

## Step 6 — Grid test (sma_window x asset class x vol regime)

Grid: `sma_window` in [100, 150, 200, 250], symbols equity=[QQQ, SPY],
crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3. 48 cells total.

- **pass_fraction: 0.250 (12/48)**
- by_asset_class: equity 12/24 passed; **crypto 0/24 passed** (decisive reject)
- by_vol_regime: low 8/16; mid 4/16; high 0/16 (same recurring pattern:
  trend-following edge concentrates in low-vol regimes)
- best_cell: SPY, sma_window=200, vol_regime=low, Sharpe 2.85

## Step 7 — Full-sample Sharpe by sma_window (QQQ, SPY)

| sma_window | QQQ Sharpe | SPY Sharpe |
|---|---|---|
| 100 | 0.915 | 0.969 |
| 150 | 1.237 | 0.959 |
| 200 | **1.253** | 0.990 |
| 250 | 1.035 | 0.819 |

QQQ's best config (sma_window=200, matching the source's own default) clears
1.0 Sharpe cleanly; SPY tops out at 0.990 (a coin-flip near-miss, same
pattern seen for other trend strategies in this repo).

### Single-config validation (QQQ, sma_window=200)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.253 | 1.0 |
| Max drawdown | ✅ | 0.219 | 0.25 |
| Transaction cost survival (10bps/trade, 12 trades) | ✅ | 1.241 (net Sharpe) | 0.5 |
| Walk-forward (4 splits, manual date-slice; vectorbt splitter API bug as noted in prior entries) | ✅ | 0.75 (3/4 splits positive: 1.28, -0.86, 1.35, 0.98) | 0.75 |
| Parameter sensitivity (4-value QQQ grid, rel. std) | ✅ | 0.128 | 0.5 |

**QQQ: all 5 validators pass — accepted.** Notably only 12 round-trip
trades over 7.7yr (~1 trade every 233 trading days) — the lowest trade
frequency of any accepted strategy in this repo so far, consistent with
the source's own observation that a single-MA rule reacts faster / trades
somewhat more than a two-MA crossover but is still a low-frequency,
low-maintenance signal.

### SPY near-miss (sma_window=200)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.990 | 1.0 |
| Max drawdown | ✅ | 0.208 | 0.25 |
| Transaction cost survival (22 trades) | ✅ | 0.956 | 0.5 |

### Crypto (BTC/USDT, ETH/USDT)

0/24 grid cells passed — decisively rejected, consistent with the
repo's established pattern of trend-following strategies underperforming
crypto's higher realized-vol profile.

## Outcome

**Accepted for QQQ** (sma_window=200). SPY near-miss (Sharpe 0.990, one
basis point shy). Crypto rejected decisively.
