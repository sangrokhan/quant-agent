# Backtest Report: Golden Triangle Pullback-Pivot Confirmation (TASC Sept 2014, Hudgin)

**Strategy file:** `strategies/2026-09-17_golden_triangle_pullback_pivot.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2014/09/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored
on the initial keyword query; Google search fallback used for keyword
discovery and to locate the exact traders.com Traders' Tips URL)

## Hypothesis

A discrete 3-phase state machine (WaitingForPivot -> WaitingForPullback ->
WaitingForConfirm) translated faithfully from Charlotte Hudgin's TradeStation
EasyLanguage code: a confirmed swing-high pivot with widening "whitespace"
between price and its 50-day SMA (linear-regression slope of price-minus-MA
accelerating), followed by an orderly pullback to the MA (not on heavy
volume, i.e. not a breakdown), followed by a volume-confirmed resumption
above the MA, signals long entry. Exit on close < MA or a 15-day time-stop
(article/TASC code specifies no exit; this is a conservative mechanical
choice consistent with the entry's trend-following premise).

## Best config (from Step 6 grid, `pivot_strength=2, vol_confirm_mult=0.9`)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | FAIL (-0.024) | PASS (1.077) |
| Max Drawdown (<=0.25) | PASS (0.078) | PASS (0.037) |
| TC survival (10bps/trade, net Sharpe>=0.5) | FAIL (-0.065) | PASS (0.999) |
| Walk-forward (manual 4-way contiguous split, >=75% pass) | FAIL (1/4 = 25%) | PASS (4/4 = 100%) |
| Parameter sensitivity (relative_std <= 0.5) | FAIL (2.44) | PASS (0.28) |
| Trades | 10 | 16 |

Crypto (BTC/USDT, ETH/USDT): decisive reject -- Sharpe fails both (0.126,
0.154), TC-survival fails both (0.017, 0.060), MDD fails ETH/USDT.

## Step 6 grid summary (pivot_strength in {2,3} x vol_confirm_mult in {0.9,1.1}, 3 vol terciles, equity+crypto)

- `pass_fraction`: 10/48 = 0.208
- `by_asset_class`: equity 3/24 passed, crypto 7/24 passed (crypto passes
  are shallow-Sharpe/small-MDD low-vol-tercile cells that don't survive the
  full-sample validator suite above -- narrow grid-cell passes are not the
  same as a robust accept)
- `by_vol_regime`: low 2/16, mid 3/16, high 5/16
- `best_cell`: pivot_strength=2, vol_confirm_mult=0.9, SPY, low-vol, Sharpe 1.73
- `worst_cell`: pivot_strength=2, vol_confirm_mult=0.9, QQQ, low-vol, Sharpe -1.11

## Decision

**Accept for SPY only** (all 5 validators pass at pivot_strength=2,
vol_confirm_mult=0.9). **Reject for QQQ** (Sharpe/TC/walk-forward/param-
sensitivity all fail -- the pattern's sparse ~10-16 trade count over 7.5
years makes it fragile to exact pivot geometry, which happens to align with
SPY's price action but not QQQ's over this sample). **Reject for crypto**
decisively (BTC/USDT, ETH/USDT both fail Sharpe and TC-survival).

Scope: narrow accept, SPY-only equity trend-continuation-after-pullback
signal, ~2 trades/year at this parameterization. Not broad enough to be
called a robust cross-asset edge -- record this narrow scope so future
loops don't over-trust it outside SPY.
