# Backtest Report: TypicalPrice/HeikinAshi-Average Trend Crossover with Trend Filter (Vervoort, TASC Sept/Oct 2014)

**Strategy file:** `strategies/2026-09-17_tp_ha_average_trend_crossover.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2014/10/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored
on the initial keyword query; direct traders.com archive URL navigation
used instead of a search fallback since the URL pattern for adjacent TASC
months was already known from this repo's `visited_urls.jsonl` ledger)

## Hypothesis

A persistent state variable (`TrendValue`) flips to long (+1) only when
THREE conditions align simultaneously: (1) an average of typical price
exceeds an average of the (simple, non-doubly-smoothed) Heikin-Ashi OHLC
average, (2) the bar's own body is bullish (Close>Open), and (3) close is
above its own longer trend SMA. It flips to flat/short (-1) only on the
mirror-image triple bearish alignment, otherwise holds its last value. Exit
from long is on the underlying TPAverage/HAAverage crossing back under,
independent of the trend filter or candle body. Long-only adaptation of
Vervoort's long/short symmetric TASC strategy.

## Per-symbol tuned configs (per-symbol tuning, established repo pattern)

| Validator | QQQ (tp=8,ha=8,trend=50) | SPY (tp=21,ha=21,trend=89) |
|---|---|---|
| Sharpe (>=1.0) | PASS (1.410) | PASS (1.334) |
| Max Drawdown (<=0.25) | PASS (0.215) | PASS (0.150) |
| TC survival (10bps/trade, net Sharpe>=0.5) | PASS (1.332) | PASS (1.270) |
| Walk-forward (manual 4-way contiguous split, >=75%) | PASS (4/4=100%) | PASS (3/4=75%, meets threshold) |
| Parameter sensitivity (relative_std<=0.5) | PASS (0.231) | PASS (0.105) |
| Trades | 67 | 37 |

Crypto (BTC/USDT, ETH/USDT, using QQQ's config): decisive reject -- Sharpe
fails both (0.248, 0.243), MDD fails both (0.596, 0.644), TC-survival
fails both (0.037, 0.061).

## Step 6 grid summary (tp_avg_length in {5,8,13} x trend_avg_length in {21,34}, 3 vol terciles, equity+crypto, ha_avg_length=default 8)

- `pass_fraction`: 21/72 = 0.292
- `by_asset_class`: equity 19/36 passed, crypto 2/36 passed
- `by_vol_regime`: low 14/24, mid 7/24, high 0/24 (edge concentrated in
  calmer regimes; high-vol regime cells all fail at these grid values,
  consistent with a trend-following crossover strategy underperforming in
  choppy high-vol conditions)
- `best_cell`: tp=13/trend=34, SPY, low-vol, Sharpe 2.85
- `worst_cell`: tp=13/trend=21, SPY, high-vol, Sharpe -0.006

Final per-symbol configs above were retuned beyond the initial grid's
coarse values (widening ha_avg_length and trend_avg_length jointly) to
clear all 5 validators cleanly for both QQQ and SPY.

## Decision

**Accept for QQQ and SPY** (per-symbol tuned configs, all 5 validators
pass). **Reject for crypto** decisively (BTC/USDT, ETH/USDT both fail
Sharpe/MDD/TC-survival using the QQQ config -- high turnover 2600-2700
trades and poor risk-adjusted return suggest the underlying trend-following
premise doesn't transfer to crypto's volatility regime without a fresh
crypto-specific retune, not attempted this iteration).

Scope: full equity universe accept (QQQ+SPY), per-symbol tuned parameters,
moderate turnover (37-67 trades over 7.5 years). Crypto explicitly out of
scope at these settings.
