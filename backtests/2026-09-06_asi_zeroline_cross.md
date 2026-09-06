# Wilder Accumulative Swing Index (ASI) Zero-Line Cross

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_asi_zeroline_cross.py`
**KB id:** 2026-09-06-131

## Hypothesis

Per cTrader's Accumulative Swing Index documentation: ASI_t = ASI_{t-1} +
SI_t (Wilder's Swing Index, 1978, "New Concepts in Technical Trading
Systems"), long entry when ASI crosses above zero (bullish momentum),
exit when ASI crosses below zero; stop-loss just below the last swing
low. First strategy in this repo using Wilder's original Swing Index /
ASI construction (distinct from RSI/ADX/ATR, his other well-tested
indicators, and distinct from prior zero-cross oscillator strategies
since ASI's formula jointly uses O/H/L/C with a limit-move constant).

**Source:** https://help.ctrader.com/indicators/built-in/trend/accumulative-swing-index/
(browser_exec — formula, buy/sell zero-cross rules, stop placement) +
https://www.quantifiedstrategies.com/accumulative-swing-index/ (browser_exec —
corroborating background, trading rules paywalled).

## Grid test (limit_move=[1,3,5] x asi_ma_window=[3,5,8] x max_hold_days=[15,25], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- **0/216 cells passed** — fully decisive rejection across both asset
  classes and all three vol regimes.
- Best cell: limit_move=1.0, asi_ma_window=3, max_hold_days=25, QQQ
  high-vol, Sharpe 0.758 (still below the 1.0 threshold).

## Decision: **REJECT**

Grid pass_fraction 0.0 (0/216) — no config/asset/regime cell clears the
Sharpe threshold. Skipped the single-config validator suite (Sharpe/MDD/
walk-forward/etc.) since the grid result is already fully decisive with no
promising cell to validate further.
