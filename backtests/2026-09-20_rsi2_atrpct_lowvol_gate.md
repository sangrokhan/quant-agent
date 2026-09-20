# RSI(2) + ATR% Low-Vol Gate — Backtest Report (2026-09-20)

**Strategy file:** `strategies/2026-09-20_rsi2_atrpct_lowvol_gate.py`
**Hypothesis source:** [StatOasis — "Do Volume and Volatility Filters
Actually Improve RSI(2)? 15,552 Backtests Say Mostly No"](https://statoasis.com/overfit/research/boost-your-rsi2-strategy-for-sp500-by-48-with-this-volume-filter)
(Ali Casey, updated Sep 17 2026), visited via `browser_exec` this iteration.

## Hypothesis

Source's own 80-filter sweep on Connors' plain RSI(2) mean-reversion
strategy found exactly one filter that reliably helped: gating entries to
only fire when ATR% (ATR/close) is below its own trailing 100-day rolling
median (low-vol regime). This improved profit factor in 75.0% of 96
matched pairings and cut worst drawdown by 5.6pp, while retaining 50.8% of
signals (much better retention than volume filters). Adapted directly:
long when RSI(2) < entry_threshold AND ATR% <= its own 100-day rolling
median; exit when RSI(2) > exit_threshold or after max_hold_days time-stop.

## Grid test (Step 6)

`param_grid={"entry_threshold": [5.0, 10.0], "exit_threshold": [60.0,
70.0], "max_hold_days": [5, 10]}`, `symbols={"equity": ["QQQ","SPY"],
"crypto": ["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`. 96 total cells.

- **pass_fraction: 0.292** (28/96)
- by_asset_class: equity 28/48 passed; **crypto 0/48 passed (decisive fail)**
- by_vol_regime: low 8/32; mid 15/32; high 5/32
- best_cell: entry_threshold=5.0, exit_threshold=70.0, max_hold_days=10,
  SPY, mid-vol, Sharpe 1.70
- worst_cell: entry_threshold=10.0, exit_threshold=70.0, max_hold_days=5,
  ETH/USDT, high-vol, Sharpe -0.69

## Single-config validation (Step 7) — grid-best config
(entry_threshold=5.0, exit_threshold=70.0, max_hold_days=10), full-period
2016-01-01 to 2026-09-01

| Metric | QQQ | SPY | Threshold | Pass |
|---|---|---|---|---|
| Sharpe (full period) | 0.786 | **1.178** | >= 1.0 | QQQ FAIL / SPY PASS |
| Max drawdown | 4.88% | 5.44% | <= 25% | PASS (both) |
| Net Sharpe after 5bps/trade costs | 0.693 | 1.031 | >= 0.5 | PASS (both) |
| Walk-forward pass fraction (4 splits) | 1.00 | 1.00 | >= 0.75 | PASS (both) |
| Parameter sensitivity (relative std, 8-combo sweep) | 0.109 | 0.086 | <= 0.5 | PASS (both) |

## Decision: ACCEPTED (SPY only)

SPY clears every validator cleanly: Sharpe 1.178, max drawdown a very tight
5.44%, transaction-cost-survival Sharpe 1.031, walk-forward 4/4, and very
low parameter sensitivity (0.086 relative std) — this is a robust, low-risk
mean-reversion strategy on SPY. QQQ is a near-miss on Sharpe alone (0.786)
with everything else passing (notably also very low drawdown, 4.88%),
worth a future targeted parameter search. Crypto is a decisive fail (0/48
grid cells) — RSI(2) mean reversion with a low-vol ATR% gate does not
transfer to BTC/ETH, consistent with this construction's equity-index
mean-reversion origin.

**Scope note for future loops:** this strategy is accepted narrowly for
SPY only with these exact parameters (entry_threshold=5.0,
exit_threshold=70.0, max_hold_days=10, atr_window=14, atr_lookback=100).
Do not assume it generalizes to QQQ or crypto without further validation.
