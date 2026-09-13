# Donchian Breakout with Continuous ATR-Relative Inverse Sizing

**Hypothesis:** Per PineScriptForge's NQ Donchian Channel Breakout Backtest
note (browser_exec) and Lumley Trading's Turtle N-unit sizing explainer:
"Scale position size down during high-volatility regimes (ATR exceeding
20-period average by 50%+) to maintain consistent dollar risk." This
iteration implements a CONTINUOUS version of that rule (not the source's
binary >50% trigger) on top of a Donchian(entry_window, exit_window)
breakout entry -- a deliberately DIFFERENT base construction from every
sizing-overlay strategy tested elsewhere in this cron trigger (all applied
to an SMA(200) trend gate, per the prior iteration's explicit
recommendation to pivot away from more risk-ratio-on-SMA-gate variants).
exposure = clip(atr_reference / atr_relative, 0, leverage_cap), where
atr_relative = ATR(atr_period) / its own rolling atr_avg_window average.
First continuous-ATR-relative-sizing strategy in this repo (existing ATR
uses: binary filters, or fixed-multiple stop-loss distances -- never a
continuous inverse-sizing dial).

**Source:** https://pinescriptforge.com (NQ Donchian Channel Breakout
Backtest, "Scale position size down during high-volatility regimes")

## Grid test summary (equity: SPY/QQQ, crypto: BTC/USDT/ETH/USDT;
entry_window in [20,40,55], atr_reference in [0.8,1.0,1.2]; exit_window=10;
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: QQQ, entry_window=20, atr_reference=0.8, low-vol, Sharpe=2.271
- worst_cell: SPY, entry_window=55, atr_reference=1.2, high-vol, Sharpe=-1.151

## Single-config validator results (best full-sample config per symbol,
found via a secondary exit_window=10/20 sweep, atr_period=14,
atr_avg_window=20, leverage_cap=1.0)

| Symbol | Config | Sharpe | Passed | MDD | Passed | Net Sharpe (5bps/trade) | Passed | Walk-fwd frac | Passed | Param sens (rel std) | Passed | Num trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | entry_window=20, exit_window=20, atr_reference=1.0 | 0.972 | No (thr 1.0) | 0.105 | Yes | 0.922 | Yes | 1.00 | Yes | 0.272 | Yes | 60 |
| QQQ | entry_window=20, exit_window=20, atr_reference=1.2 | 1.193 | Yes | 0.227 | Yes | 1.160 | Yes | 1.00 | Yes | 0.020 | Yes | 53 |

Note: `validators.check_walk_forward` has the same pre-existing tooling gap
(`vbt.utils.splitting.RangeSplitter` unavailable) — substituted a manual
4-split walk-forward (same 0.75 threshold); both symbols hit a perfect 4/4.

## Decision

**Accepted (QQQ only).** All 5 validators pass for QQQ (entry_window=20,
exit_window=20, atr_reference=1.2). SPY fails only the Sharpe threshold
(0.972 < 1.0, a near-miss by 0.028) with every other validator passing
comfortably (MDD an excellent 0.105, perfect 4/4 walk-forward, tight
parameter sensitivity 0.272) -- worth revisiting with a wider entry_window/
exit_window sweep in a future iteration. Crypto (BTC/USDT, ETH/USDT)
rejected decisively across the whole grid (0/54 cells), consistent with
nearly every trend-following construction tested in this repo.
