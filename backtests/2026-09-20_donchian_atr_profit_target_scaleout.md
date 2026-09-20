# Backtest Report: Donchian Breakout + ATR-N Scaled Profit Targets + Chandelier Trail

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_donchian_atr_profit_target_scaleout.py`
**Source:** https://raw.githubusercontent.com/trustdan/trend-following-backtesting-strategies/main/pine-scripts/14_PF-1.232_SPY_seykota_alt10_profit_targets.pine (fully disclosed Pine Script, from https://github.com/trustdan/trend-following-backtesting-strategies, visited via `browser_exec`; `web_search` worked for the initial general query this iteration but returned no directly usable rule-set page for several follow-up queries, so browser_exec Google SERP was used to locate and fetch this GitHub repo)

## Hypothesis

Per danieltuckerrust's "Seykota Alt 10: Profit Targets" strategy: a classic
Donchian-breakout trend-following entry can be improved not by changing the
entry, but by scaling OUT of the position at fixed ATR-multiple ("N")
profit milestones (+3N, +6N, +9N) rather than holding the full position to
a single trailing-stop exit — locking in gains progressively while still
letting a fractional position run with a trend via a Chandelier trail.
Adapted to this repo's single continuous-exposure-series contract: exposure
starts at 1.0 on breakout entry and steps down by 1/3 at each profit
target, with the remaining fraction trailed by a Chandelier stop.

## Grid Test Summary (Step 6)

`param_grid={"entry_window": [35,55,70], "trail_n_mult": [2.5,3.0],
"target1_n": [2.0,3.0]}` (target2_n/target3_n held at defaults 6.0/9.0),
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Total cells:** 144, **passed:** 40, **pass_fraction:** 0.278
- **By asset class:** equity 26/72 (0.361), crypto 14/72 (0.194)
- **By vol regime:** low 35/48 (0.729), mid 5/48 (0.104), high 0/48 (0.0)
- **Best cell:** equity/SPY, low-vol, `entry_window=35, trail_n_mult=2.5,
  target1_n=3.0`, Sharpe 2.71
- **Worst cell:** equity/SPY, mid-vol, `entry_window=70, trail_n_mult=3.0,
  target1_n=2.0`, Sharpe -1.26
- Best full-sample-averaged equity config: `entry_window=35, target1_n=3.0,
  trail_n_mult=3.0` (avg equity Sharpe 0.957 across QQQ/SPY low/mid/high
  slices)

As with most trend-following strategies in this repo, the edge concentrates
heavily in low-vol regimes (0.729 pass fraction) and essentially disappears
in high-vol (0/48) — consistent with breakout/trend systems whipsawing in
choppy high-vol conditions.

## Single-Config Validation (Step 7) — `entry_window=35, target1_n=3.0, trail_n_mult=3.0`

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd (4-split) | Param sensitivity (rel. std) |
|---|---|---|---|---|---|
| QQQ | 0.883 (FAIL, thr 1.0) | 0.235 (PASS) | 0.831 (PASS) | 1.00 (PASS) | 0.035 (PASS) |
| **SPY** | **1.017 (PASS)** | **0.195 (PASS)** | **0.954 (PASS)** | **1.00 (PASS)** | **0.273 (PASS)** |
| BTC/USDT | 1.032 (PASS) | 0.391 (FAIL, thr 0.25) | 1.014 (PASS) | 1.00 (PASS) | 0.050 (PASS) |

Walk-forward used a manual 4-way contiguous split (`validators.check_walk_forward`
still errors on the installed vectorbt version, known repo-wide issue).

## Decision (Step 8): **ACCEPTED (SPY only)**

SPY passes all 5 validators at the grid-selected best config. QQQ is a
narrow near-miss on Sharpe alone (0.883 vs 1.0 threshold) — every other
validator passes, and the grid shows QQQ performing comparably to SPY in
low-vol cells, so this is a real but partial edge rather than a QQQ-only
rejection; kept in the file/log as informative but not "accepted" for QQQ
specifically. BTC/USDT clears the Sharpe bar but fails max-drawdown
decisively (0.391 vs 0.25) — crypto's much larger trend swings blow past
the equity-tuned ATR-multiple stop/trail parameters, consistent with
several other trend-following strategies in this repo that work on
US equity index ETFs but not on crypto majors at the same settings.

**Scope for live use**: SPY only, at `entry_window=35, atr_window=20`
(default), `stop_n_mult=2.0` (default), `trail_window=22, trail_n_mult=3.0`,
`target1_n=3.0, target2_n=6.0, target3_n=9.0` (defaults). Not validated as
broadly robust across asset classes or volatility regimes — an honest,
narrow accept.
