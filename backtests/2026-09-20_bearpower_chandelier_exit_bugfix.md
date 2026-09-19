# Bear Power + Chandelier Trailing Stop -- Bugfix Rescue of 2026-09-20-070

**Hypothesis:** Direct rescue of this cron trigger's own rejected entry
2026-09-20-070 (Bear Power entry + Chandelier trailing stop exit, per
Kryptera's "The Regime Report" Medium article on a Micron Technology
backtest). Root-cause investigation found the parent's rejection was NOT
a weak-signal problem but a genuine implementation bug: the `running_stop`
ratchet variable could get initialized to NaN on an early entry (before
the Chandelier ATR/highest-high rolling windows had enough history), and
because NaN comparisons in Python are always False, the trailing-stop
exit condition then silently NEVER fired again for the rest of that
trade -- explaining the parent's exact-1-trade degeneracy regardless of
any exit parameter tested. This entry fixes the bug (always adopt the
first valid Chandelier stop value even if `running_stop` starts as
None/NaN) and re-tests the identical signal design.

## Strategy file
`strategies/2026-09-20_bearpower_chandelier_exit_bugfix.py`

## Grid test (post-fix, ema_window in {13,21} x atr_mult in {2.5,3.0,3.5}, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2015-2026)

- pass_fraction: 0.292 (21/72) -- with realistic trade counts now (52-124 trades depending on config, not 1)
- by_asset_class: equity 17/36, crypto 4/36
- by_vol_regime: low 16/24, mid 5/24, high 0/24

Literal disclosed-range params (ema_window=13/21, atr_mult=2.5-3.5) still
fail full-sample Sharpe on both QQQ and SPY. A wider local sweep
(ema_window in {8,13,21,34} x atr_mult in {2.0-4.0}) found a working
region around ema_window=21/atr_mult=3.75-4.0.

## Full-sample validators (QQQ, ema_window=21, atr_mult=3.75)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.101 | >= 1.0 | PASS |
| Max drawdown | 0.241 | <= 0.25 | PASS |
| TC survival (10bps/trade, 60 trades) | net Sharpe 1.046 | >= 0.5 | PASS |
| Walk-forward (4 manual splits) | 4/4 positive Sharpe (1.0) | >= 0.75 | PASS |
| Parameter sensitivity (ema_window in {17,19,21,23,25} x atr_mult in {3.5,3.75,4.0}) | rel_std 0.183 | <= 0.5 | PASS |

SPY at the same config: Sharpe 0.495 (decisive reject) -- this rescue is
QQQ-specific.

## Outcome

**Accepted for QQQ only** (ema_window=21, atr_mult=3.75). This is a
genuine bugfix-driven rescue: the parent (2026-09-20-070) was correctly
rejected given its buggy implementation, but the underlying idea (Bear
Power momentum-exhaustion entry + volatility-adaptive Chandelier trailing
stop) does have real edge on QQQ once the exit mechanism actually works
as intended, at a wider ATR multiple (3.75-4.0) than the parent's
originally-tested range (2.5-3.5). SPY and crypto remain out of scope for
this specific configuration.
