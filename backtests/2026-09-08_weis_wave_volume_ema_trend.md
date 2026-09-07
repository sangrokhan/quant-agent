# Weis Wave Volume + 200-EMA Trend Filter

**Hypothesis:** Per David Weis's Weis Wave Volume (WWV, 1990s VSA technique),
transcribed at https://pineify.app/pine-script/indicators/weis-wave-volume :
WWV accumulates total volume during each directional price "wave" (a run of
consecutive same-direction closes), resetting at every direction flip. The
source's "Strategy 3 (Wave Volume + EMA Trend Filter)": only trust
accumulation signals (an up-wave whose running volume already exceeds the
prior completed up-wave's total) when price is above a 200-EMA; exit on a
distribution signal (a down-wave's volume exceeding the last up-wave's
volume) or the EMA trend flipping bearish, plus a max-hold time-stop.

Source: https://pineify.app/pine-script/indicators/weis-wave-volume
(logged in `knowledge_base/visited_pages.jsonl`; quantifiedstrategies.com's
Wave Volume page was also attempted but blocked by a bot-verification wall
-- logged as unhelpful).

## Step 6 — Grid test (ema_window in {100,200}, max_hold_days in {10,20,30},
equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3,
2019-01-01 to 2026-09-01)

- Total cells: 72, passed: 12, **pass_fraction = 0.167**
- By asset class: equity 12/36 passed, **crypto 0/36 passed** (decisive fail)
- By vol regime: **low 12/24 passed, mid 0/24, high 0/24** — the edge is
  entirely concentrated in the low-volatility tercile across BOTH QQQ and
  SPY and ALL 6 param combos tested (very consistent within that slice:
  Sharpe range 1.78-2.34), but mid/high-vol regimes are a decisive 0/48
  fail.
- Best cell: SPY, ema_window=200, max_hold_days=30, low-vol regime,
  Sharpe 2.324

## Step 7 — Single-config validators (ema_window=200, max_hold_days=30,
SPY, full unconditional 2019-2026 sample)

| Validator | Result |
|---|---|
| Sharpe (>= 1.0) | **FAIL 0.570** |
| Max Drawdown (<= 0.25) | PASS 0.246 (near the limit) |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade, 161 trades) | **FAIL 0.260** |
| Walk-forward (manual 4-split, sharpe>0 required) | PASS 3/4 splits positive (0.75) |
| Parameter sensitivity (relative_std <= 0.5, over the 6 SPY param combos from Step 6's grid low-vol-only avg Sharpe) | PASS 0.169 (mean 0.727, std 0.123 -- stable across ema_window/max_hold_days) |

## Outcome: **REJECTED**

The strategy is stable and robust WITHIN the low-vol regime (parameter
sensitivity passes cleanly, walk-forward mostly holds, and 12/24 low-vol
cells pass across both QQQ and SPY at every parameter combo tested) — but
the full, unconditional multi-regime sample fails Sharpe (0.570 < 1.0) and
decisively fails transaction-cost survival (161 trades at a strategy that
holds positions through mid/high-vol whipsaws too, net Sharpe collapses to
0.260). Unlike the earlier GARCH vol-regime-gate strategy (rejected as a
near-miss), this one is not close on the primary Sharpe threshold and adds
a large trade-count drag. A future iteration could revisit this by adding
an EXPLICIT low-vol regime gate (similar to 2026-09-03-001's construction)
on top of the WWV+EMA signal, which the grid strongly suggests would
recover the edge cleanly (12/24 low-vol pass rate vs 0/48 elsewhere) while
avoiding the mid/high-vol whipsaw trade churn that killed transaction-cost
survival here.
