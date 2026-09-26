# Backtest Report: HYG Weak-Monday Overnight Reversal

**Strategy file:** `strategies/2026-09-27_hyg_weak_monday_overnight_reversal.py`
**Date:** 2026-09-27
**Source:** https://quantpedia.com/overnight-reversal-effects-in-the-high-yield-market/
(Cyril Dujava, Quantpedia, Aug 2024), read via `browser_exec` (web_extract's
DuckDuckGo backend cannot extract page content).

## Hypothesis

HYG (iShares iBoxx $ High Yield Corporate Bond ETF) shows a systematic
overnight (close-to-open) return premium concentrated in the
Monday-close->Tuesday-open session, most pronounced when Friday's
close-to-Monday's-close return was negative (a "weak Monday"). Distinct
from the already-tested/rejected `2026-09-20_hyg_turnaround_tuesday.py`
(id 2026-09-20-059), which holds the FULL Monday-close->Tuesday-CLOSE
session; this strategy isolates only the OVERNIGHT leg
(Monday close -> Tuesday OPEN), per the source's own finding that "HYG
fares the best during the overnight sessions... daily sessions... hurt and
do not contribute towards the asset's gains... at all."

## Grid test summary (Step 6)

Grid: `gate_weekday=0` (Monday), `down_thresh in [-0.01, -0.005, 0.0]` x
equity {HYG, JNK} + crypto {BTC/USDT, ETH/USDT} x 3 vol-regime terciles,
2010-01-01 to 2026-09-01 (HYG/JNK full available history).

- **Overall pass_fraction: 0.139 (5/36 cells)**
- **by_asset_class:** equity 5/18 passed (0.278); crypto 0/18 (0.0)
- **by_vol_regime:** low 0/12; mid 0/12; **high 5/12** — edge, such as it
  is, only clears the grid's Sharpe/MDD bar in HIGH-vol terciles (best_cell
  HYG high-vol, `down_thresh=0.0`, Sharpe 1.62), not low/mid.
- **worst_cell:** BTC/USDT low-vol, Sharpe -0.82 (crypto has no discrete
  Monday/Tuesday session boundary at all — falsification-check confirms the
  mechanism is credit/equity-market-structure specific, as expected).

## Standard validators (Step 7) — best config: `down_thresh=0.0` (unconditional Monday overnight hold)

| Validator | HYG | JNK |
|---|---|---|
| Sharpe (>=1.0) | 0.910 — **FAIL** | 0.834 — **FAIL** |
| Max Drawdown (<=0.25) | 0.032 — pass (very low, as expected for a bond ETF) | 0.038 — pass |
| TC survival (5bps/trade, min net Sharpe 0.5) | 0.024 — **FAIL** | 0.016 — **FAIL** |
| Parameter sensitivity (relative std <=0.5, sweep of `down_thresh`) | 0.173 — pass | 0.208 — pass |

(Walk-forward not run this iteration — the unconditional full-sample Sharpe
already fails decisively on both symbols, so a 4-way walk-forward split
would not change the accept/reject outcome; noted per RESEARCH_LOOP.md
Step 7's "run whichever subset is relevant" guidance.)

## Decision: **REJECTED (decisive)**

Full-sample Sharpe falls short of the 1.0 bar on both HYG (0.910) and JNK
(0.834) even at the best (unconditional, `down_thresh=0.0`) grid config,
and net-of-cost Sharpe collapses to near-zero (0.02-0.024) once a modest
5bps/trade cost is applied — this is a genuine, small, real overnight
premium (consistent with the source's own low-turnover framing "the
advantage of not trading each nightly session... is a better win-to-loss
ratio, lower turnover"), but it is too small in absolute Sharpe terms to
clear this repo's 1.0 bar and does not survive transaction costs at the
~370-390 nonzero-exposure-day frequency this construction trades at.

The grid's own vol-regime breakdown (only high-vol terciles pass, 5/12)
suggests a genuine but narrow edge worth flagging for a future loop: a
volatility-regime-gated variant (only take the Monday-overnight trade when
realized vol is elevated) could be worth a follow-up rescue attempt, since
the raw effect concentrates there rather than being uniform. Not pursued
further this iteration given time/token budget — filed as a near-miss/
rescue candidate in `notes`.
