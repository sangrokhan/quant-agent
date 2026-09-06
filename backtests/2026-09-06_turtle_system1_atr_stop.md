# Turtle Trading System 1 (20-day breakout) + 2N ATR Stop-Loss + Skip-After-Win

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_turtle_system1_atr_stop.py`
**KB id:** 2026-09-06-125

## Hypothesis

The original 1983 Turtle Trading System 1 rule: enter long at the close on a
new 20-day high; place an initial protective stop at entry - 2N (N = 20-day
average True Range, per Turtle convention); exit on whichever comes first of
the ATR-based stop or a new 10-day low. Also applies System 1's "skip the
next breakout if the most recent trade in this instrument was a winner"
filter. This differs from the already-accepted plain Donchian 20/10 breakout
(2026-09-04-054) by adding a volatility-sized stop-loss exit and the
skip-after-win entry filter, both absent from -054.

**Source:** Google AI-overview summary of Turtle Trading System rules (web_search
returned no results; fell back to browser_exec on
`https://www.google.com/search?q=Turtle+Trading+System+rules+20-day+55-day+breakout+entry+exit+N+ATR`),
citing JournalPlus / TrendSpider / Trading Dude / Ultima Markets snippets.

## Grid test (entry_window=[20,30,40] x stop_atr_mult=[1.5,2.0,3.0], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 27/108 cells passed (equity 27/54, **crypto 0/54 decisively rejected**)
- By vol regime: low 18/36, mid 9/36, **high 0/36** (works in calm/trending markets only)
- Best cell: entry_window=20, stop_atr_mult=1.5, QQQ low-vol, Sharpe 2.93
- Best config by symbol-average: entry_window=20, stop_atr_mult=3.0 → QQQ avg Sharpe 1.52 across regimes; SPY avg Sharpe 1.15 at the same config (also decent).

## Single-config validators (QQQ, entry_window=20, stop_atr_mult=3.0, full sample 2019-09 to 2026-09)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.327 | ≥ 1.0 |
| Max drawdown | PASS | 17.85% | ≤ 25% |
| TC survival (10bps, 34 trades) | PASS | net Sharpe 1.279 | ≥ 0.5 |
| Walk-forward (manual 4-split) | PASS | 4/4 splits positive Sharpe | ≥ 75% |
| Parameter sensitivity (9-cell QQQ sweep) | PASS | relative_std 0.129 | ≤ 0.5 |

SPY sanity check at the same config: Sharpe 1.008 (consistent, also passes the 1.0 bar).

## Decision: **ACCEPT** (equity only — QQQ/SPY)

All validators pass cleanly on the primary QQQ config, with consistent
results on SPY. Crypto is decisively rejected (0/54 grid cells) and high-vol
regimes fail entirely (0/36) — this strategy should be scoped to
equity/low-mid-vol regimes only, consistent with several prior accepted
strategies in this repo (Donchian -054, OBV -027, CMF -043, A/D -047, Force
Index -049 all show the same QQQ/SPY-only, non-crypto pattern).
