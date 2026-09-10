# 2026-09-10 — EMA(50/200) Bias + EMA(20) Pullback + RSI(14) Trigger + MACD Confirmation "Trend Pullback" Stack

**Status: REJECTED**

## Hypothesis

Source: https://indicators101.com/how-to-combine-multiple-indicators-without-overloading/
("How To Combine Multiple Indicators (Without Overloading)", Oct 2025).

The article's "one-tool-per-job" framework prescribes a 5-job "Stack A —
Trend Pullback" combo for longs: bias (50EMA>200EMA & close>200EMA), setup
(pullback touch to 20EMA), trigger (RSI(14) dips to 40-50 then closes back
above 50), confirmation (MACD line > 0), and ATR-based risk (approximated
here with a pullback-break/bias-break/time-stop exit rather than an
intrabar ATR stop-loss, since `generate_returns` only tracks a 0/1 position
series). Hypothesis: requiring ALL FOUR conditions to align simultaneously
reduces false signals versus any single constituent indicator alone.

Distinct from every existing single-indicator variant in this repo (plain
EMA crossovers, RSI midline reclaim alone, MACD zero-line alone) — first
strategy combining all four jobs from this specific "one-tool-per-job"
framework simultaneously.

## Grid test (Step 6)

`param_grid={"pullback_band": [0.008, 0.012, 0.016], "rsi_low": [35, 40, 45]}`,
`symbols={"equity": [QQQ, SPY], "crypto": [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, period 2017-01-01 to 2026-09-01 → **108 cells**.

- **pass_fraction: 0.0 (0/108)** — decisive failure across the entire grid.
- by_asset_class: equity 0/54, crypto 0/54.
- by_vol_regime: low 0/36, mid 0/36, high 0/36.
- best_cell: QQQ, low-vol regime, `pullback_band=0.012, rsi_low=35.0` →
  Sharpe 0.9909 (still below the 1.0 threshold).
- worst_cell: QQQ, high-vol regime, `pullback_band=0.016, rsi_low=45.0` →
  Sharpe -0.659.

Full grid JSON: `grid_result_ema_pullback_stack.json`.

## Single-config validation (best full-sample QQQ config)

Config: `pullback_band=0.012, rsi_low=35.0` (the grid's best individual
cell), full sample 2017-2026, QQQ:

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **False** | 0.452 | 1.0 |
| Max drawdown | True | 0.134 | 0.25 |
| Transaction-cost survival (10bps/trade, 81 trades) | **False** | 0.280 (net Sharpe) | 0.5 |

Walk-forward and parameter-sensitivity skipped: the grid's decisive 0/108
pass fraction and full-sample Sharpe (0.452, well below threshold) already
make the accept/reject call unambiguous — no further validator spend is
warranted (`suggested_workload=normal`, but grid+Sharpe+MDD+TC already
conclusive per RESEARCH_LOOP.md Step 7 guidance to run "whichever subset is
relevant").

## Conclusion

**Rejected.** Requiring all four indicator-stack conditions (bias + pullback
setup + RSI reclaim + MACD>0 confirmation) simultaneously produces a signal
that is too infrequent/low-quality to clear the Sharpe bar on any
asset/vol-regime combination in the grid, and the isolated best cell
(QQQ low-vol, Sharpe 0.99) doesn't survive to the full sample (Sharpe drops
to 0.452) — consistent with the source article's own framing as a
"clean, high-probability" but conservative filter rather than a
high-Sharpe standalone system. The multi-condition AND-gate appears to
filter out too much of the tradable signal rather than improving quality
enough to compensate.
