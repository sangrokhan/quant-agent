# Backtest Report: Bulkowski Three Rising Valleys Breakout (SPY accepted, QQQ rejected)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_three_rising_valleys_breakout.py`
**Sources:** Google SERP snippets of https://thepatternsite.com/ThreeRisingValleys.html
(direct fetch 404'd; identification rule confirmed verbatim in Google's SERP
snippet: "the bottom of each valley must be above the prior one") and the
site's companion Quiz page, corroborated by trading.biz's independent
description ("three valleys, each higher than the last (HL)") and a
dokumen.pub excerpt of Bulkowski's own Encyclopedia of Chart Patterns
("Prices must close above the confirmation point before a trade is
placed"). web_search's DDGS backend returned unrelated/garbage results
this iteration, browser_exec Google fallback used throughout.

## Hypothesis
Three Rising Valleys: three consecutive swing lows, each strictly above
the prior one (monotonically rising support), signal an established
uptrend structure. Entry confirms on a close above the pattern's
"confirmation point" (highest intervening peak between the first and
third valley, Bulkowski's standard convention). Per an independently
confirmed Google AI-overview summary of Bulkowski's own published
performance-rank tables, this pattern ranks among the "Top 10
Continuations, Upward Breakouts, Bull Markets" (51% average rise, tied
with Rectangle Top) — a comparably strong prior to this repo's
just-accepted Rectangle Top strategy (2026-09-24-099). First Three Rising
Valleys entry in this repo (0 prior index hits) — distinct from every
prior pattern tested (not a converging-trendline consolidation, not a
neckline-and-rebound reversal structure).

## Grid summary (Step 6)
`param_grid={"swing_window": [3, 5], "lookback_bars": [40, 60, 80]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3` (normal workload).

- total_cells: 72, passed_cells: 23, **pass_fraction: 0.319**
- by_asset_class: equity 15/36, crypto 8/36
- by_vol_regime: low 3/24, mid 11/24, high 9/24 (unusually, edge is
  NOT concentrated in low-vol — this pattern's strongest single cell was
  low-vol SPY, but the overall pass distribution skews mid/high-vol,
  distinct from most trend-following strategies in this repo)
- best_cell: swing_window=5, lookback_bars=80, SPY, low-vol, Sharpe 2.450

## Single-config validators (best cell: swing_window=5, lookback_bars=80)

### SPY
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample, 70 trades) | **PASS** | 1.416 | >= 1.0 |
| Max drawdown | **PASS** | 0.040 | <= 0.25 (very strong margin) |
| Transaction cost survival (10bps/trade) | **PASS** | net Sharpe 0.930 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | known repo `vectorbt.utils.splitting` bug |
| Parameter sensitivity (12-combo sweep) | **PASS** | rel_std 0.312 | <= 0.5 |

### QQQ (same config)
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample, 66 trades) | **FAIL** | 0.646 | >= 1.0 |
| Max drawdown | PASS | 0.108 | <= 0.25 |
| Transaction cost survival | **FAIL** | net Sharpe 0.415 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | same repo bug |
| Parameter sensitivity | **FAIL** | rel_std 0.530 | <= 0.5 |

## Decision: ACCEPT (SPY only), REJECT (QQQ)
SPY clears every runnable validator with a notably strong max-drawdown
margin (0.040 vs 0.25 threshold). QQQ fails Sharpe, TC-survival, and
parameter-sensitivity at the identical config — the pattern's edge does
not transfer cleanly to QQQ. Crypto not separately single-config-validated
(grid showed 8/36 crypto cells passing, weaker than equity) — flagged as a
future per-symbol fine-tune candidate but not pursued this iteration.
