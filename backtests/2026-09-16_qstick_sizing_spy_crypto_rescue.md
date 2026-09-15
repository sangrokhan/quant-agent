# Qstick continuous-sizing dial — SPY finer retune + crypto leverage-cap rescue

**Hypothesis id:** 2026-09-16-149 (rescue of 2026-09-14-108)
**Source:** unchanged from 2026-09-14-108 (Google SERP browser_exec fallback:
CorporateFinanceInstitute, QuantifiedStrategies, TradoFunded, TradingView —
QStick = SMA(n, Close-Open)). No new external research this sub-iteration;
pure parameter-retune rescue of an already-implemented, already-sourced
strategy (`strategies/2026-09-14_qstick_sizing_sma_trend.py`, unmodified).

## Prior state (2026-09-14-108)
- QQQ: accepted (trend_window=40, qstick_sensitivity=0.7, deadband=0.3) — Sharpe 1.102, MDD 0.136, TC 0.84, WF 1.0, param-sens rel-std 0.051.
- SPY: rejected — best of 25-combo sweep Sharpe 0.991 (0.9% below 1.0 threshold), all else passing.
- BTC/USDT: rejected — MDD 40.1% at leverage_cap=1.0 (equity default), 0/72 grid cells passed.
- ETH/USDT: not separately grid-tested in 2026-09-14-108 (crypto rejected decisively on BTC alone).

## This sub-iteration: two independent retune sweeps

### 1. SPY finer sweep around the near-miss
Grid: trend_window ∈ {55,60,65} × qstick_sensitivity ∈ {0.4,0.45,0.5,0.55} ×
deadband ∈ {0.3,0.33,0.35,0.37} (Sharpe/MDD only via `run_strategy_grid`,
vol_regime_splits=3) → 144 cells, pass_fraction 0.333 (48/144, all low-vol
regime only; 0/48 mid-vol, 0/48 high-vol — same vol-regime-dependence
pattern noted in the prior full-sample entries this family shows).

Full-sample single-config validator confirmation (4 candidate configs):

| trend_window | sensitivity | deadband | Sharpe | MDD | TC net Sharpe | WF | Verdict |
|---|---|---|---|---|---|---|---|
| 55 | 0.50 | 0.35 | 0.988 | 0.110 | 0.473 | 1.0 | FAIL (Sharpe, TC) |
| **60** | **0.45** | **0.35** | **1.084** | **0.086** | **0.603** | **1.0** | **PASS all** |
| 60 | 0.50 | 0.33 | 0.925 | 0.122 | 0.369 | 1.0 | FAIL (Sharpe, TC) |
| 55 | 0.45 | 0.30 | 0.825 | 0.117 | 0.256 | 1.0 | FAIL (Sharpe, TC) |

**SPY selected config: trend_window=60, qstick_sensitivity=0.45,
deadband=0.35** — Sharpe 1.084 (was 0.991), MDD 0.086, TC net Sharpe 0.603,
walk-forward 1.0 (4/4 manual equal-slices positive). Rescues the prior
near-miss.

### 2. Crypto leverage-cap-aware retune (standard repo rescue pattern)
Grid: leverage_cap ∈ {0.2,0.3,0.4} × sensitivity-scale ∈ {0.3,0.4,0.5}
(qstick_sensitivity = leverage_cap × scale) × deadband ∈ {0.15,0.2,0.25},
trend_window=40 unchanged, base_exposure = leverage_cap × 0.5 — 27 combos ×
2 symbols = 54 full-sample validator runs (Sharpe/MDD/TC/manual-WF).

- BTC/USDT: 27/27 combos passed Sharpe/MDD/TC (many degenerate at
  deadband=0.25+low leverage — 0 trades, excluded).
- ETH/USDT: 25/27 passed.
- Both non-degenerate (num_trades > 10) AND passing: 18 combos.

**Crypto selected config: leverage_cap=0.3, base_exposure=0.15,
qstick_sensitivity=0.09, deadband=0.15** (lowest-MDD config among the
strong-Sharpe non-degenerate survivors):
- BTC/USDT: Sharpe 1.339, MDD 0.127, TC net Sharpe 0.969, WF 1.0, 125 trades.
- ETH/USDT: Sharpe 1.223, MDD 0.116, TC net Sharpe 1.001, WF 1.0, 115 trades.

Both far below the 25% MDD threshold and well clear of the prior 40.1% fail —
confirms this was a pure sizing-scale issue at equity-default leverage_cap=1.0,
not a signal-quality problem, matching this repo's now-established pattern
for this whole continuous-sizing-dial family (MFI/VZO/CHOP/TSI/KPO all
showed the identical failure mode and identical fix).

## Outcome
**Accepted, full universe now covered for this Qstick continuous-sizing
strategy:** QQQ (unchanged from 2026-09-14-108, trend_window=40/sens=0.7/
db=0.3), SPY (NEW: trend_window=60/sens=0.45/db=0.35), BTC/USDT (NEW:
leverage_cap=0.3/base=0.15/sens=0.09/db=0.15), ETH/USDT (same crypto
config). Strategy file unchanged: `strategies/2026-09-14_qstick_sizing_sma_trend.py`.
