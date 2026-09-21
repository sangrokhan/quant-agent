# Backtest Report: Unique Three Rivers Bearish Continuation Short

**Strategy file:** `strategies/2026-09-21_unique_three_rivers_bearish_continuation_short.py`
**Knowledge base id:** 2026-09-21-243

## Hypothesis

Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(pattern #40), Unique Three Rivers is traditionally a bullish reversal but
the source's own backtest finds it behaves more like a bearish
continuation. Operationalized as: bar1 long bearish; bar2 bearish with a
long lower wick, gaps up but makes a lower low than bar1; bar3 small
bullish, contained below bar2's body.

## Bug found and fixed during this iteration

The first grid run silently returned 0 trades for ALL equity cells due to
a `TypeError: boolean value of NA is ambiguous` from
`body2.replace(0, pd.NA)` followed by a `>=` comparison, caught by the grid
harness's per-cell exception handling and recorded as zero-signal rather
than crashing the whole run. Fixed by using
`body2.replace(0, float("nan"))` instead. Noted in the knowledge base for
future iterations writing similar zero-body-guard code.

## Grid summary (Step 6, after fix)

Grid: `trend_lookback in {10,20} x long_body_mult in {0.8,1.0,1.2} x
target_atr_mult in {1.5,2.0,3.0}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 216 cells.

- **pass_fraction: 0.0 (0/216)** -- decisive fail
- by_asset_class: equity 0/108, crypto 0/108
- by_vol_regime: low 0/72, mid 0/72, high 0/72
- best_cell: ETH/USDT, low-vol regime, Sharpe only 0.318 (far below
  threshold)
- Signal is very rare (QQQ 0 trades, SPY 4 trades at tested params)

## Decision

**Rejected.** Decisive 0% grid pass fraction across all cells; full
validators.py skipped given the non-borderline result.
