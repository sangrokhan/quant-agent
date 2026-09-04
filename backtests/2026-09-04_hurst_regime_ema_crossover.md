# Hurst Exponent Regime-Gated EMA Crossover (QQQ) — REJECTED

**Hypothesis:** Rolling Hurst exponent H (R/S rescaled-range analysis,
Harold Hurst 1951) measures long-range persistence: H > 0.5 = trending
regime, H < 0.5 = mean-reverting/anti-persistent, H ~ 0.5 = random walk.
Gate a classic fast/slow EMA crossover trend-following signal to only fire
when H exceeds a threshold (confirmed trending regime).

**Source:** https://fractalcycles.com/guides/hurst-exponent-explained
(concept/definition only, no concrete backtested strategy rules given —
entry/exit mechanics and thresholds are this repo's own operationalization
of the H>0.5 trending-regime concept). Also attempted
https://www.quantifiedstrategies.com/hurst-exponent/ but it is bot-blocked
("Verifying that you are not a robot...").

**Novelty:** Distinct from every prior trend-regime filter in this repo
(VHF 2026-09-04-152, RWI 2026-09-04-153, ADX, Choppiness Index — all
measure trend STRENGTH from price-range/ATR ratios) — Hurst instead
measures statistical long-memory/persistence via rescaled-range scaling
exponent, a fundamentally different construction. First Hurst-exponent
strategy in this repo.

## Best config: hurst_window=100, hurst_threshold=0.55, fast_span=20, slow_span=50, max_hold_days=20 (QQQ, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.425 | >= 1.0 | **FAIL** |
| Max drawdown | 11.73% | <= 25% | PASS |
| Transaction cost survival (5bps/trade, 32 trades) | net Sharpe 0.371 | >= 0.5 | **FAIL** |
| Parameter sensitivity (relative std across hurst_threshold x fast_span, QQQ) | 0.812 | <= 0.5 | **FAIL** |
| Walk-forward | SKIPPED | n/a | Same repo-wide `vectorbt.utils.splitting` API issue noted in 2026-09-04-154 |

## Step 6 grid summary (hurst_threshold in [0.5,0.55,0.6] x fast_span in [20,30], symbols QQQ/SPY equity + BTC/ETH crypto, vol_regime_splits=3)

- **Overall pass_fraction: 18.1%** (13/72 cells)
- **By asset class:** equity 13/36 (36.1%); crypto 0/36 (0%) — no edge on crypto whatsoever.
- **By vol regime:** low 7/24, mid 6/24, **high 0/24** — the trending-regime gate specifically fails to help during high-vol periods (likely whipsaws even when H is nominally elevated, since realized vol and Hurst estimation noise both spike together).
- **Best cell:** QQQ, hurst_threshold=0.5, fast_span=30, low-vol regime, Sharpe 2.30 — but this is a single favorable slice, not representative of the full-sample behavior.

## Decision: REJECT

Grid cells pass in scattered low/mid-vol slices (18% pass_fraction,
concentrated on QQQ), but the full-sample single-config validator suite at
the grid's best-looking QQQ config fails on Sharpe (0.43 vs 1.0 required),
transaction-cost survival (0.37 net Sharpe vs 0.5 required), and parameter
sensitivity (0.81 relative std vs 0.5 max — the strategy's Sharpe swings
from -0.09 to 0.62 just from nudging hurst_threshold/fast_span slightly,
including a NEGATIVE Sharpe at hurst_threshold=0.6). The regime-slice
successes look like a form of regime cherry-picking rather than a durable
edge; the underlying EMA-crossover trend-following signal itself is likely
the dominant (weak) driver, with the Hurst gate not adding enough
discriminative power to compensate for reduced trade frequency (32 trades
over ~7.5 years). Also fully fails on both crypto pairs across the entire
grid. Rejected as a repeatable/robust strategy at this window/parameter
scope; the Hurst-regime CONCEPT may still be worth revisiting as a filter
layered onto a different (mean-reversion, not trend-following) base
signal in a future iteration, since H < 0.5 (anti-persistent) explicitly
predicts mean-reversion should work — that inverse pairing was not tested
here.
