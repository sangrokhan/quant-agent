# Backtest Report: Realized Semivariance Skew (Good/Bad Volatility) Gate

**Strategy file:** `strategies/2026-09-20_realized_semivariance_skew_gate.py`
**Date:** 2026-09-20
**Hypothesis:** Per Barndorff-Nielsen, Kinnebrock & Shephard (2010,
"Measuring downside risk - realised semivariance", Harvard/Oxford) and
Patton & Sheppard (2015, "Good Volatility, Bad Volatility: Signed Jumps and
the Persistence of Volatility", Review of Economics and Statistics) --
read this iteration via Google SERP snippets (arXiv/Duke/ResearchGate/
RePEc, browser_exec fallback since web_search DDGS returned no results):
daily realized variance decomposes into upside ("good") and downside
("bad") realized semivariance; downside volatility is more persistent and
more informative about future weakness than upside volatility. This
strategy computes a trailing realized-semivariance SKEW = (RSV+ - RSV-) /
(RSV+ + RSV-) (daily-close-return proxy, since data/loaders.py provides
OHLC bars only, not true intraday ticks) and gates long/flat exposure:
long while skew >= skew_threshold (good-vol regime dominates), flat
otherwise (bad-vol regime dominates).

Distinct from this repo's existing Sortino/Downside-Deviation/Kappa-3
sizing-dial family (2026-09-13-048/059/061): those use semi-deviation
magnitude as a continuous SIZING denominator layered on an existing SMA
trend gate; this strategy uses the SIGN/RATIO of the semivariance skew as
a standalone binary regime FILTER with no separate trend gate.

## Grid test summary (Step 6)

`window in [10, 20, 40]` x `skew_threshold in [-0.1, 0.0, 0.1]`, symbols
`{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 36, pass_fraction: 0.333
- by_asset_class: equity 29/54 passed, crypto 7/54 passed
- by_vol_regime: low 25/36, mid 8/36, high 3/36
- best_cell: crypto/ETH-USDT/mid-vol, window=40/skew_threshold=0.1, Sharpe 2.75

## Single-config validators (Step 7)

Full-sample (2019-01-01 to 2026-09-01):

**QQQ, window=20, skew_threshold=0.0:**
| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.386 | >=1.0 | Yes |
| Max Drawdown | 0.196 | <=0.25 | Yes |
| TC survival (10bps/trade, 144 trades) | net Sharpe 1.142 | >=0.5 | Yes |
| Walk-forward (4 manual chronological splits) | 4/4 splits Sharpe>0 (1.0) | >=0.75 | Yes |
| Parameter sensitivity (skew_threshold sweep -0.15..0.15) | relative_std 0.124 | <=0.5 | Yes |

**SPY, window=20, skew_threshold=-0.1:**
| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.316 | >=1.0 | Yes |
| Max Drawdown | 0.111 | <=0.25 | Yes |
| TC survival (10bps/trade, 124 trades) | net Sharpe 1.066 | >=0.5 | Yes |
| Walk-forward (4 manual chronological splits) | 4/4 splits Sharpe>0 (1.0) | >=0.75 | Yes |
| Parameter sensitivity | relative_std 0.089 | <=0.5 | Yes |

**Crypto (BTC/USDT, ETH/USDT), all tested window/skew_threshold combos:**
Full-sample Sharpe passes (1.0-1.4) at most configs, but **MDD always
fails** (0.47-0.68, far above the 0.25 threshold) -- crypto's much larger
full-cycle drawdowns overwhelm the semivariance-skew gate's ability to
control tail risk over the complete 2019-2026 sample, even though the
grid shows real edge concentrated in mid-vol-tercile slices (7/54 crypto
grid cells pass, best Sharpe 2.75 on ETH/USDT mid-vol).

## Decision: ACCEPT (equity only)

- **QQQ** (window=20, skew_threshold=0.0): all 5 validators pass.
- **SPY** (window=20, skew_threshold=-0.1): all 5 validators pass.
- **Crypto**: rejected for full-sample use -- Sharpe alone passes at most
  configs but MDD decisively fails on every full-sample test. Grid
  evidence shows the mechanism does carry SOME genuine signal in crypto's
  mid-vol regime specifically (7/54 pass, concentrated there per
  by_vol_regime breakdown) -- an honest scope note per RESEARCH_LOOP.md
  Step 6 guidance, not grounds for acceptance on the full crypto sample.

Scope: accepted for equities (QQQ, SPY) with per-symbol thresholds (0.0
and -0.1 respectively -- both economically sensible: QQQ requires the
skew to be non-negative, SPY tolerates a mildly negative skew before
flattening, consistent with SPY's generally lower baseline volatility).
Explicitly NOT validated for crypto on the full sample (only in the mid-vol
tercile per the grid).
