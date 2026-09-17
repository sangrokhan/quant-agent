# Backtest Report: Modified True Range "Goal %" Continuous Sizing Dial (Lindgren, TASC Feb/Apr 2015)

**Strategy file:** `strategies/2026-09-17_mtr_goal_pct_sizing_dial.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2015/04/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored;
direct traders.com archive URL navigation to a previously-unvisited month)

## Hypothesis

Lindgren's Modified True Range (MTR = max(|High-PrevClose|, |Low-PrevClose|))
"Goal Achievement %" (rolling frequency of MTR clearing a goal_atr_mult x
ATR(40) threshold, a naturally bounded [0,100] statistic) reframed as a
continuous sizing dial: high recent volatility-achievement frequency scales
exposure up, gated by an SMA(trend_window) uptrend filter with a deadband.
First Modified True Range strategy in this repo.

## Best config (goal_atr_mult=1.0, deadband=0.2, trend_window=50)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | FAIL (0.915) | PASS (1.020) |
| Max Drawdown (<=0.25) | PASS (0.159) | PASS (0.164) |
| TC survival (net Sharpe>=0.5) | PASS (0.712) | PASS (0.720) |
| Walk-forward (>=75%) | FAIL (3/4=75%... wait, this is PASS) actually PASS | PASS (4/4) |
| Parameter sensitivity | PASS (0.015) | PASS (0.023) |
| Trades | 120 | 117 |

Crypto (BTC/USDT, ETH/USDT): decisive reject -- Sharpe fails both (0.217,
0.198), MDD fails both (0.404, 0.457), TC-survival fails both (negative).

A broad QQQ-specific retune (goal_atr_mult in {0.6-1.7}, deadband in
{0.05-0.5}, trend_window in {20-150}) found NO configuration clearing
Sharpe>=1.0 while keeping MDD<=0.25 -- QQQ's rejection is a genuine
Sharpe-ceiling issue, not a tuning gap.

## Step 6 grid summary (goal_atr_mult in {0.8,1.0,1.2} x deadband in {0.1,0.2}, 3 vol terciles, equity+crypto, 72 cells)

- `pass_fraction`: 28/72 = 0.389
- `by_asset_class`: equity 18/36, crypto 10/36 (crypto grid-cell passes are
  shallow low-vol-tercile only, do not survive full-sample validator suite)
- `by_vol_regime`: low 22/24, mid 6/24, high 0/24 (edge concentrated in
  calmer regimes -- consistent with the exposure dial scaling UP during
  high recent-volatility-achievement, which paradoxically underperforms
  during genuinely high-vol regimes where the deadband/trend-gate combo
  doesn't fully protect against whipsaws)
- `best_cell`: goal_atr_mult=1.0/deadband=0.2, QQQ, low-vol, Sharpe 2.73
- `worst_cell`: goal_atr_mult=0.8/deadband=0.2, QQQ, high-vol, Sharpe -0.31

## Decision

**Accept for SPY only** (all 5 validators pass). **Reject for QQQ**
(Sharpe fails at every searched config -- ceiling around 0.91-0.92).
**Reject for crypto** decisively.

Scope: narrow accept, SPY-only, ~117 trades/7.5yr. Not a broad cross-asset
edge -- recorded here so a future loop doesn't over-trust it beyond SPY.
