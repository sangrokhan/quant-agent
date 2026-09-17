# Backtest Report: RSI With Trend / Swing-Retracement Trend Filter (Kevin Luo, TASC June 2015)

**Strategy file:** `strategies/2026-09-17_rsi_swing_trend_filter.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2015/06/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored;
direct traders.com archive URL navigation to a previously-unvisited month)

## Hypothesis

RSI oversold (<oversold) crossunder entries gated by a novel swing-
retracement trend-state machine: the trend flips to "up" only when a new
confirmed swing high represents a genuine `retrace_pct`% move away from the
last swing reference (once established, subsequent swing highs just need
to exceed the prior extreme, no retrace_pct re-required). Exit on RSI
crossing overbought or the trend state flipping to "down".

## Config: oversold=45, retrace_pct=8 (grid best) and SPY-specific same config

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | FAIL (0.644) | PASS (1.231) |
| Max Drawdown (<=0.25) | FAIL (0.265) | PASS (0.166) |
| TC survival (net Sharpe>=0.5) | PASS (0.612) | PASS (1.200) |
| Walk-forward (>=75%) | PASS (3/4=75%) | PASS (4/4) |
| Parameter sensitivity (<=0.5) | FAIL (1.724) | PASS (0.452) |
| Trades | 25 | 20 |

## QQQ-specific retune attempt (oversold=40, retrace_pct=12, rsi_length=21)

| Validator | QQQ |
|---|---|
| Sharpe | PASS (1.901) |
| Max Drawdown | PASS (0.095) |
| TC survival | PASS (1.877) |
| Walk-forward | PASS (4/4) |
| Parameter sensitivity | FAIL (0.588) |
| Trades | 12 |

A broader local search around this QQQ retune (oversold +/-5, retrace_pct
+/-2) found no config simultaneously clearing Sharpe/MDD AND parameter
sensitivity -- the strategy is inherently low-trade-count (12-25 trades
over 7.5yr) on QQQ, making its Sharpe estimate fragile to small parameter
perturbations. This is a genuine parameter-sensitivity rejection, not a
tuning gap.

## Step 6 grid summary (oversold in {35,40,45} x retrace_pct in {8,10,15}, 3 vol terciles, equity+crypto, 108 cells)

- `pass_fraction`: 17/108 = 0.157
- `by_asset_class`: equity 17/54, crypto 0/54 (crypto decisively rejected --
  BTC/USDT and ETH/USDT both show near-zero/negative Sharpe with the QQQ
  config, ~184-202 trades)
- `by_vol_regime`: low 12/36, mid 0/36, high 5/36
- `best_cell`: oversold=40/retrace_pct=10, SPY, high-vol, Sharpe 2.08
- `worst_cell`: oversold=40/retrace_pct=10, ETH/USDT, low-vol, Sharpe -1.98

## Decision

**Accept for SPY only** (oversold=45, retrace_pct=8, rsi_length=14 default;
all 5 validators pass). **Reject for QQQ** (param-sensitivity fails at
every config found that also clears Sharpe/MDD -- inherently fragile due
to low trade count on this symbol). **Reject for crypto** decisively.

Scope: narrow accept, SPY-only, ~20 trades/7.5yr (roughly 2.7 trades/year).
The swing-retracement trend filter is a genuinely novel mechanism worth
revisiting with a different base oscillator (e.g. Stochastic instead of
RSI) if a future loop wants to explore this trend-detection idea further.
