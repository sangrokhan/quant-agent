# Backtest Report: Ultimate Oscillator (Larry Williams) Threshold-Cross

**Strategy file:** `strategies/2026-09-04_ultimate_oscillator_threshold.py`
**Knowledge base id:** 2026-09-04-050

## Hypothesis

Per Google AI-overview + QuantifiedStrategies.com's own simpler backtested
rule: the Ultimate Oscillator (UO, Larry Williams, blends buying pressure
vs true range across 7/14/28-period windows weighted 4:2:1) crossing
below a low threshold (40) signals a long entry; crossing above a high
threshold (50) signals exit.

Source: Google AI-overview (`web_search` failed 3x with a DDGS/Yahoo TLS
connection error, fell back to `browser_exec` immediately).

## Grid test summary (Step 6)

Grid: `buy_threshold` in {30, 40} x `sell_threshold` in {50, 60} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 48 cells.

- `pass_fraction`: 0.042 (2/48) — among the lowest of any strategy tested.
- `by_asset_class`: equity 2/24, crypto 0/24
- `by_vol_regime`: low 1/16, mid 1/16, high 0/16

## Full-sample sweep (QQQ / SPY)

| buy_threshold | sell_threshold | QQQ Sharpe (trades) | SPY Sharpe (trades) |
|---|---|---|---|
| 30 | 50 | 0.247 (7)  | -0.012 (8) |
| 30 | 60 | 0.461 (7)  | 0.228 (8)  |
| 40 | 50 | 0.438 (35) | 0.415 (39) |
| 40 | 60 | 0.416 (27) | **0.844** (34) |

Best full-sample Sharpe across all 8 (4 param combos x 2 symbols) results
is 0.844 (SPY, buy_threshold=40, sell_threshold=60), decisively below the
1.0 threshold. Given the uniformly weak full-sample Sharpe, the remaining
validator suite was skipped per Step 7 minimum-subset guidance.

## Outcome

**Rejected.** Crypto rejected decisively (0/24 grid cells).

## Notes

First Ultimate Oscillator (3-timeframe blended buying-pressure/true-range
ratio, distinct from every single-window oscillator already tested)
strategy in this repo. Implemented QuantifiedStrategies' own simpler,
concretely-backtested threshold-cross rule rather than the more elaborate
divergence-breakout variant (which has the same unimplementable
subjective swing-detection issue as the already-rejected RSI-divergence
strategy, 2026-09-03-019). The tighter buy_threshold=30 configs (closer
to the source's cited "oversold" level) generate very few trades (7-8
over 7.7 years) and weak/negative Sharpe; the looser buy_threshold=40
generates more trades (27-39) but still doesn't clear the threshold —
this simpler mechanical rule variant does not appear to carry a
meaningful edge on this sample.
