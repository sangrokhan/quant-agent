# Backtest report: SFP liquidity-sweep reversal, low-vol-regime gated (fix attempt)

**Strategy file:** `strategies/2026-09-09_sfp_liquidity_sweep_volregime_gated.py`
**KB id:** 2026-09-09-089

## Hypothesis

Direct fix for near-miss/rejected 2026-09-09-087 (plain SFP liquidity-sweep
reversal): that iteration's grid showed the edge concentrated almost
entirely in low-vol regimes (pass 17/48 low vs 1/48 mid, 0/48 high). This
variant adds an explicit low-vol-regime gate (same construction as accepted
`2026-09-03_bb_meanrev_qqq_volregime.py`: 20d realized vol vs trailing
252d median) so the signal only fires/holds during low-vol regimes, instead
of trading the raw pattern through all regimes.

## Grid test (Step 6)

Same param grid as 2026-09-09-087 (`swing_lookback=[5,10,15]`,
`risk_reward=[1.5,2.0]`, `max_hold_days=[10,20]`; equity QQQ/SPY, crypto
BTC/USDT/ETH/USDT; vol_regime_splits=3; 2019-2026).

- **pass_fraction:** 0.083 (12/144) — actually *lower* than the ungated
  version's 0.125 (18/144).
- **by_asset_class:** equity 12/72, crypto 0/72.
- **by_vol_regime:** low 12/48, mid 0/48, high 0/48 — the gate successfully
  suppresses ALL mid/high-vol trading (as designed), but the low-vol slice
  itself didn't improve (12/48 vs 17/48 ungated) since the regime gate now
  also cuts some low-vol-regime trades whose *entry* vol regime flipped mid-
  hold, and best-cell Sharpe (2.34) is close to but not better than the
  ungated version's low-vol best cell (2.50).

## Single-config validation (Step 7) — best config (swing_lookback=10, risk_reward=2.0, max_hold_days=10)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.201 — **FAIL** | 0.108 — **FAIL** |
| Max drawdown (<=0.25) | 0.175 — pass | 0.090 — pass |
| TC survival (net Sharpe >=0.5) | -0.029 — **FAIL** | -0.136 — **FAIL** |
| Walk-forward (manual 4-split, >=75%) | 3/4 (0.75) — pass | 2/4 (0.5) — **FAIL** |
| Parameter sensitivity (relative std <=0.5) | 3.29 — **FAIL** | 3.33 — **FAIL** |

The vol-regime gate did NOT fix the core problem: full-sample Sharpe is
still far below threshold (0.20/0.11), and parameter sensitivity got
*worse* (3.3 vs 0.92/0.26 ungated) because the gate makes trade counts and
outcomes much more sensitive to exact swing_lookback/risk_reward choices
(fewer total trades, so each param combo's outcome swings more).

## Decision

**Rejected** (both QQQ and SPY) — the regime-gate fix hypothesis is falsified:
gating to low-vol regime did not rescue full-sample Sharpe/TC-survival, and
made parameter sensitivity meaningfully worse. This is a genuinely useful
negative result: a straightforward "add a vol-regime gate" patch is not a
universal fix for a pattern whose grid-sliced Sharpe looks good only in one
regime slice — the regime-sliced numbers (2.34-2.50) reflect within-regime
performance over a small, cherry-picked sub-sample, not a tradable
full-history edge once entry/exit timing and regime transitions are handled
honestly. Future iterations revisiting SFP/liquidity-sweep ideas should be
skeptical of "just add a vol filter" as an easy fix and instead look for a
different underlying signal improvement (e.g. a require-2-touches
confirmation, or trading only around specific known swing highs rather than
any N-bar rolling low).
