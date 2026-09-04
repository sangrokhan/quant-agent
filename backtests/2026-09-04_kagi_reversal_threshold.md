# Backtest Report: Kagi Chart Reversal-Threshold Trend Follower

**Strategy file:** `strategies/2026-09-04_kagi_reversal_threshold.py`
**Hypothesis id:** 2026-09-04-137
**Source:** https://www.tradejini.com/blogs/kagi-charts-guide

## Hypothesis

Kagi charts plot a vertical line that continues in one direction until
price reverses by more than a fixed threshold (`reversal_pct`) from the
running swing extreme; the line is "thick" (yang, bullish) while in an
uptrend and "thin" (yin, bearish) while in a downtrend. Per the source,
the flip from thin to thick (a "waist") is the systematic long entry, and
the flip from thick to thin (a "shoulder") is the exit. This is the first
Kagi/percentage-reversal-threshold system tested in this repo (no fixed
lookback window at all -- purely a running high/low-water-mark with a
percentage reversal trigger).

## Single-config validators (SPY, reversal_pct=0.05, max_hold_days=80 -- Step 6 grid's best low-vol cell config)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full period) | ❌ | 0.387 | ≥ 1.0 |
| max_drawdown | ❌ | 0.365 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 28 trades) | ❌ | net Sharpe 0.354 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` still broken in this install) | ❌ | 2/4 splits positive Sharpe | ≥ 0.75 pass fraction |
| parameter_sensitivity | ✅ | relative std 0.283 (4-combo grid) | ≤ 0.5 |

## Step 6 grid summary

`param_grid={reversal_pct:[0.03,0.05], max_hold_days:[40,80]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
48 cells total.

- **pass_fraction:** 0.271 (13/48)
- **by_asset_class:** equity 13/24 passed (54%); crypto 0/24 passed (0%)
- **by_vol_regime:** low 8/16; mid 5/16; high 0/16
- **best_cell:** reversal_pct=0.05, max_hold_days=80, SPY, low-vol regime, Sharpe 3.01
- **worst_cell:** reversal_pct=0.05, max_hold_days=40, QQQ, high-vol regime, Sharpe -1.04

## Decision: REJECT (decisive)

4 of 5 validators fail on the full-period single-config run -- notably
max drawdown at 0.365 is far outside the 0.25 threshold (a large
percentage-reversal-threshold like 5% lets the strategy ride sizeable
adverse moves before flipping, producing deep drawdowns during real
corrections/bear markets even though the grid's isolated low-vol slice
looked strong). Crypto rejected decisively (0/24). Not worth carrying
forward without a much tighter reversal threshold or an added
max-drawdown-aware exit overlay on top of the pure Kagi flip.
