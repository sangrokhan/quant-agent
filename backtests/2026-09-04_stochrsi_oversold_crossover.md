# Stochastic RSI (StochRSI) Oversold-Zone %K/%D Crossover — Backtest Report

**Hypothesis:** StochRSI (Chande & Kroll, 1994) applies the stochastic
formula to RSI values rather than raw price, giving a faster/more sensitive
0-100 oscillator with tighter 20/80 oversold/overbought bands than plain
RSI's 70/30. Bullish entry: %K crosses above %D while both are below the
oversold threshold (per navia.co.in's concrete crossover rule). Exit: %K
crosses back below %D.

Source: https://www.quantifiedstrategies.com/stochastic-rsi/ (exact
numeric rule paywalled, general formula/thresholds given; source's own
SPY backtest reports 78% win rate but with an undisclosed exact rule) +
navia.co.in search snippet (concrete crossover-in-zone rule). web_search
failed repeatedly with a DDGS/Yahoo TLS connection error, fell back to
browser_exec Google search.

## Step 6 — Grid test (oversold threshold x asset class x vol regime)

Grid: `oversold` in [20.0, 30.0] (rsi_window=14, stoch_window=14 fixed),
symbols equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3.
24 cells total.

- **pass_fraction: 0.042 (1/24)**
- by_asset_class: equity 1/12; crypto 0/12
- by_vol_regime: low 1/8; mid 0/8; high 0/8
- best_cell: SPY, oversold=30, vol_regime=low, Sharpe 1.35 (single tercile,
  not representative)

## Full-sample Sharpe by config (QQQ, SPY)

| oversold | QQQ Sharpe (trades) | SPY Sharpe (trades) |
|---|---|---|
| 20.0 | -0.207 (70) | 0.368 (64) |
| 30.0 | 0.098 (97) | 0.301 (91) |

**No config on either symbol approaches the 1.0 Sharpe threshold** — best
full-sample result is SPY at oversold=20 with Sharpe 0.368, still far
short. High trade frequency (64-97 round-trips over 7.7yr) with no
meaningful net edge, consistent with the source's own headline statistic
(78% win rate but only 4.85% annual return / 10% time invested on their
own undisclosed-rule SPY backtest) suggesting the win-rate number
overstates the strategy's practical edge once position sizing/frequency
are accounted for.

## Outcome

**Rejected across all configs and asset classes (decisive).** No
single-config validator suite run given the uniformly poor full-sample
Sharpe. Distinct from the accepted RSI-momentum-centerline strategy
(2026-09-04-077, which uses raw RSI zero/centerline crosses rather than a
stochastic-of-RSI oversold-zone crossover) — confirms that not every RSI
variant transfers into an edge on this repo's daily-bar sample even when a
source reports an attractive headline win rate.
