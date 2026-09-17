# Backtest Report: Keltner Channel Oscillator %B Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-18_keltner_pctb_sizing_sma_trend.py`
**Hypothesis id:** 2026-09-18-001
**Source:** https://tradesmart.com/blog/technical-analysis-keltner-channel-oscillator/ (already on file, prior entry 2026-09-10-067)

## Hypothesis

Keltner Channel Oscillator = (Price - KC_lower)/(KC_upper - KC_lower) - 0.5, a %B-style
normalized position within an EMA-basis + ATR-width Keltner Channel. The repo's one prior
Keltner Oscillator entry (2026-09-10-067) used it as a binary mean-reversion threshold-cross
trigger and was rejected. This iteration reframes the same oscillator as a CONTINUOUS SIZING
dial (rescaled `osc*2` clipped to [-1,1]) within an SMA(trend_window) uptrend gate, with a
deadband to control turnover -- the same technique this repo has used to rescue several other
binary-rejected oscillators (Bollinger %B, ESD Bands %B, Kirshenbaum, STARC, etc.).

## Grid Test Summary (Step 6)

Grid: `sensitivity` in {0.5, 0.7}, `deadband` in {0.2, 0.3}, `leverage_cap` in {1.0, 0.4},
symbols equity {QQQ, SPY} + crypto {BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- total_cells: 96, passed_cells: 53, **pass_fraction: 0.552**
- by_asset_class: equity 28/48, crypto 25/48 (edge holds broadly across both asset classes)
- by_vol_regime: low 28/32, mid 18/32, high 7/32 (edge concentrated in low/mid-vol regimes,
  degrades sharply in high-vol regime -- consistent with mean-reversion-flavored sizing dials)
- best_cell: SPY, low-vol, sensitivity=0.5/deadband=0.3/leverage_cap=0.4, Sharpe 2.51
- worst_cell: QQQ, high-vol, sensitivity=0.5/deadband=0.2/leverage_cap=1.0, Sharpe -0.38

## Single-Config Validation (Step 7)

Config: `trend_window=40, ema_window=20, atr_window=20, atr_mult=2.0, base_exposure=0.4,
sensitivity=0.5, deadband=0.3`, leverage_cap=1.0 for equity / 0.4 for crypto.

| Symbol   | Sharpe | MDD    | TC-survival net Sharpe | Walk-forward (4-slice) | Param sensitivity (rel std) | Verdict |
|----------|--------|--------|------------------------|------------------------|------------------------------|---------|
| QQQ      | 1.068  | 0.145  | 0.832                  | 1.0 (4/4 pos)           | 0.043                         | **ACCEPT** |
| SPY      | 0.975  | 0.068  | 0.670                  | 1.0 (4/4 pos)           | 0.095                         | REJECT (Sharpe near-miss) |
| BTC/USDT | 1.169  | 0.222  | 1.073                  | 1.0 (4/4 pos)           | 0.011                         | **ACCEPT** |
| ETH/USDT | 1.097  | 0.278  | 1.039                  | 1.0 (4/4 pos)           | 0.017                         | REJECT (MDD 0.278>0.25) |

Walk-forward used a manual 4-equal-slice fallback (repo's `vbt.utils.splitting.RangeSplitter`
is broken in this vectorbt install, per prior repo notes) -- all 4 slices positive Sharpe for
every symbol.

## Decision (Step 8)

**Accepted for QQQ (equity) and BTC/USDT (crypto)** at leverage_cap=1.0 / 0.4 respectively,
all 5 validators pass for both. SPY and ETH/USDT are both near-miss (SPY Sharpe 0.975<1.0;
ETH/USDT MDD 0.278>0.25, close to the 0.25 threshold) -- left as future per-symbol retune
candidates rather than pursued further this iteration (workload=max but iteration budget
already spent on research/grid/validation for this one strategy).
