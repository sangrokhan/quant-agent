# Bear Power Zero-Cross Entry with Chandelier Trailing Stop Exit

**Hypothesis:** Per a Medium article by Kryptera, "The Regime Report: How
to Find the Strategy Inside Your Strategy" (summarized via Google
AI-overview, direct article link unresolved via click-through this
iteration -- web_search DDGS backend TLS/connection-reset errors
throughout): headline example strategy pairs a Bears Power entry with a
Chandelier Trailing Stop exit, backtested on Micron Technology (MU) over
42 years / 76 trades. The AI-overview summary itself flags this as
plausibly overfit to a single ticker without walk-forward validation.
Adapted here: Bear Power = Low-EMA(13) rising-while-negative (bears losing
conviction) AND EMA itself rising (uptrend), long entry; exit via a
classic ATR-based Chandelier trailing stop (highest high over N periods
minus atr_mult x ATR(N), ratcheting only upward while in position).

## Strategy file
`strategies/2026-09-20_bearpower_chandelier_exit.py`

## Grid test summary (ema_window in {13,21} x atr_mult in {2.5,3.0,3.5}, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2015-2026)

- pass_fraction: 0.333 (24/72 cells) -- looks strong at grid level
- by_asset_class: equity 24/36, crypto 0/36
- by_vol_regime: low 12/24, mid 12/24, high 0/24

## Full-sample validators reveal a degenerate signal: only 1 trade over the entire 2015-2026 sample

| Symbol | Config | Sharpe | MDD | Trades |
|---|---|---|---|---|
| QQQ | all configs tested | 1.043 (nominal PASS) | 0.356 FAIL | **1** |
| SPY | all configs tested | 0.879 FAIL | 0.341 FAIL | **1** |

The entry condition (Bear Power rising-while-negative AND EMA itself
rising, both required simultaneously) is far too restrictive in practice
-- it fires almost exactly ONCE across the full 11-year sample regardless
of `ema_window`/`atr_mult` (the exit parameters don't matter because entry
essentially never re-triggers). With only 1 trade, the "strategy" is
effectively an accidental long-term buy-and-hold from whatever date the
one signal fired, which explains both the apparently-decent QQQ Sharpe
(riding the broad 2015-2026 uptrend) and the poor MDD (no risk management
benefit from a strategy that is, in practice, just "buy once and mostly
hold"). This is not a usable signal regardless of the encouraging-looking
grid pass_fraction (which is driven by regime-sliced windows that happen
to overlap with the single long holding period, not by genuine repeated
signal quality).

## Outcome

**Rejected** -- degenerate/non-functional signal (effectively 1 trade
over 11 years). This also serves as a caution consistent with the source
article's own self-aware framing: a single-ticker, single-period backtest
(here, MU 42 years / 76 trades) can look impressive while hiding a signal
that barely fires in-sample on a different (though related) universe --
exactly the "regime report" style diagnostic the source article itself
recommends running before trusting a strategy. No further parameter
tuning attempted this iteration; the entry logic itself needs to be
loosened (e.g., drop the simultaneous EMA-rising requirement, or use a
less strict Bear-Power-rising definition) to produce a testable trade
count, which is out of scope for this iteration's budget.
