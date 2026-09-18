# Ehlers/Ric Way Zero-Lag (Error-Correcting) EMA Crossover (2026-09-18)

**Strategy file:** `strategies/2026-09-18_ehlers_zerolag_ec_ema_crossover.py`
**Hypothesis id:** 2026-09-18-113
**Source:** https://sacredtraders.com/zero-lag-well-almost-by-john-ehlers-and-ric-way/
(TASC article, read via browser_exec fallback; web_search's DDGS backend
returned only search snippets, standard for this pipeline).

## Hypothesis

Ehlers/Ric Way's "error-correcting" (EC) filter feeds a gain-scaled version
of an EMA's own per-bar error term (`Price - EC[-1]`) back into the filter:
`EC = a*(Price + Gain*(Price - EC[-1])) + (1-a)*EC[-1]`, with `Gain` searched
each bar over `[-gain_limit/10, +gain_limit/10]` to minimize `|Price - EC|`.
This produces a leading line relative to a standard EMA without the
overshoot of naive lag removal. Source's own disclosed trading rule: trade
EC/EMA crossovers, filtered by requiring the per-bar least-error magnitude
(as a % of price) exceed `thresh_pct` to suppress whipsaw when the two lines
sit nearly on top of each other. Zero prior Error-Correcting/Zero-Lag-Ric-Way
entries in this repo -- genuinely new indicator family, distinct construction
from all prior Ehlers SuperSmoother/Roofing Filter/Reflex/Trendflex/Laguerre
entries (none use an error-feedback loop).

## Grid test summary (Step 6)

Grid: `length` in {20, 32, 45} x `thresh_pct` in {0.5, 0.75}, symbols
{QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto), vol_regime_splits=3.
72 total cells.

- **Overall pass_fraction: 0.333** (24/72)
- By asset class: equity 20/36 passed (strong), crypto only 4/36 passed
  (weak) -- this mechanism is much more equity-favorable.
- By vol regime: low 16/24, mid 6/24, high 2/24 -- concentrated in low-vol
  conditions, degrading sharply in high-vol regimes.
- Best cell: equity QQQ, length=32, thresh_pct=0.75, low-vol regime,
  Sharpe 3.06.
- Worst cell: crypto ETH/USDT, length=45, thresh_pct=0.5, high-vol regime,
  Sharpe -0.84.
- Best aggregated config: **QQQ, length=32, thresh_pct=0.75** (mean grid
  Sharpe 1.65, highest of all symbol/param combos).

## Single-config validation (Step 7) — QQQ, length=32, thresh_pct=0.75

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | True | 1.457 | >= 1.0 |
| Max drawdown | True | 0.206 | <= 0.25 |
| Transaction cost survival (10bps/trade, 55 trades) | True | 1.367 (net Sharpe) | >= 0.5 |
| Walk-forward (4 contiguous splits, manual fallback) | True | 1.0 (4/4 splits Sharpe>0) | >= 0.75 |
| Parameter sensitivity (6-point grid, relative std) | True | 0.035 | <= 0.5 |

(Same `check_walk_forward` API incompatibility as this cron trigger's prior
Vortex entry -- see 2026-09-18-112 -- worked around with a manual 4-way
split.)

## Decision: ACCEPT

All 5 validators passed for QQQ at length=32, thresh_pct=0.75, with a very
low parameter-sensitivity relative std (0.035, remarkably stable across the
6-point grid). Scope: equity-only (QQQ confirmed; SPY also passed most grid
cells at mean Sharpe ~1.28-1.30 across all params, a strong secondary
candidate but not separately re-validated this iteration). Crypto is
explicitly OUT OF SCOPE for this strategy -- only 4/36 crypto grid cells
passed, concentrated at length=20 (shorter lookback), and even those did not
clear a full aggregated pass. A future iteration could investigate whether
a leverage-cap-aware crypto retune (this repo's standard rescue pattern)
salvages crypto, but that was not attempted here.
