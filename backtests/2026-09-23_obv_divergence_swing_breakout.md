# 2026-09-23 OBV Divergence Swing Breakout with ATR Stop / 2R Target (QQQ, BTC/USDT)

## Hypothesis
Source: Google AI Overview (Korean-language SERP; search: "On Balance
Volume OBV divergence trading strategy specific rule backtest"), read via
browser_exec Google SERP fallback (web_search DDGS backend errored this
query). `suggested_workload=light` this iteration, so grid scoped down to
one equity + one crypto symbol, 2 params x 2 values each.

Rule: bullish divergence between price swing lows (lower low) and OBV
swing lows (higher low), confirmed by a breakout close above the
intervening swing high; ATR(14)-based stop-loss at 1x ATR below the
divergence low; take-profit at a configurable reward:risk multiple (2R
default, tested 1.5x/2.0x); max holding period cap.

## Grid test summary (swing_window x [5,8], reward_risk x [1.5,2.0];
symbols QQQ equity, BTC/USDT crypto; vol_regime_splits=3; 24 total cells)

- pass_fraction: 0.083 (2/24)
- by_asset_class: equity 2/12, crypto 0/12
- by_vol_regime: low 0/8, mid 0/8, high 2/8
- best_cell: swing_window=5, reward_risk=1.5, equity QQQ, high-vol,
  Sharpe 1.15
- worst_cell: swing_window=5, reward_risk=1.5, crypto BTC/USDT, low-vol,
  Sharpe -1.03

Full-grid full-period (unconditional) Sharpe sweep across QQQ/SPY/BTC: best
was only 0.481 (swing_window=5, reward_risk=1.5, QQQ).

## Verdict: REJECTED

Full-period Sharpe fails on all symbols (best 0.481 vs threshold 1.0), and
the grid pass fraction is weak (0.083) with the only passing cells confined
to a single high-vol tercile on QQQ -- not a broad or robust edge. Crypto
(BTC/USDT) failed entirely across all cells. Walk-forward/tx-cost/param-
sensitivity validators skipped given the decisive Sharpe failure and light
workload budget.

Strategy file kept in `strategies/` as a record of a rejected attempt (not
live). The swing-detection + divergence + breakout-confirmation logic
itself appears functionally correct (produces sensible signal counts) but
the specific ATR-stop/2R-target risk parameters disclosed by the source did
not translate into a statistically strong edge on daily equity or
crypto-default-interval bars in this backtest window.
