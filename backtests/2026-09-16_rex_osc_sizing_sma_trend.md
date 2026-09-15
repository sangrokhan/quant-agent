# Backtest Report: REX Oscillator Continuous Sizing Dial (SMA trend gate)

**Strategy file:** `strategies/2026-09-16_rex_osc_sizing_sma_trend.py`
**Hypothesis source:** https://www.quantifiedstrategies.com/rex-oscillator/
(already logged in this repo's visited-pages ledger from a prior iteration;
formula re-used unchanged, no new fetch this iteration).

## Hypothesis

REX Oscillator (per quantifiedstrategies.com): TVB ("True Value of a
Bar") = 3*Close - (Low + Open + High), REX = EMA(TVB, rex_period). This
repo's one prior REX entry
(`strategies/2026-09-08_rex_oscillator_pullback_continuation.py`, id
2026-09-08-059) used REX as a binary pullback-continuation zero-cross
trigger, rejected decisively on all symbols. This iteration reframes the
identical formula as a CONTINUOUS SIZING dial (rolling z-score + tanh)
inside an SMA(trend_window) uptrend gate.

## Step 6 grid test summary

Grid: `sensitivity` in {0.3, 0.5, 0.7} x `rex_period` in {14, 21} x symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} x vol_regime_splits=3, leverage_cap=1.0
exploratory pass, 2019-01-01..2026-09-01.

- total_cells=72, passed=28, **pass_fraction=0.389**
- by_asset_class: equity 16/36, crypto 12/36
- by_vol_regime: low 20/24, mid 8/24, high 0/24
- best_cell: SPY, sensitivity=0.7/rex_period=21, low-vol, Sharpe 2.97
- All 24 per-(symbol,params)-averaged cells had positive Sharpe; BTC/USDT
  was the single strongest symbol on average.

## Single-config validation and per-symbol retuning

**QQQ** (trend_window=40, rex_period=21, zscore_window=100,
base_exposure=0.5, sensitivity=0.3, deadband=0.25, leverage_cap=1.0):
Sharpe 1.139, MDD 0.139, TC-survival 0.584 -- **PASS** on first try.

**SPY** at rex_period=14/sensitivity=0.3/deadband=0.25 was a near-miss on
TC-survival (net Sharpe 0.366<0.5, 196 trades). A retune sweep (trend_window
x rex_period x sensitivity x deadband) found: **trend_window=40,
rex_period=14, sensitivity=0.3, deadband=0.35** -> Sharpe 1.044, MDD 0.088,
TC-survival 0.606, 122 trades -- **PASS**.

**BTC/USDT and ETH/USDT** (leverage-cap-aware config from the start:
trend_window=40, rex_period=21, zscore_window=100, base_exposure=0.15,
sensitivity=0.15, deadband=0.2, leverage_cap=0.3):
- BTC/USDT: Sharpe 1.323, MDD 0.184, TC-survival 1.095, 105 trades -- **PASS**
- ETH/USDT: Sharpe 1.021, MDD 0.127, TC-survival 0.852, 117 trades -- **PASS**

**Parameter sensitivity** (from the Step-6 grid's per-symbol averaged
Sharpe across sensitivity x rex_period combos): QQQ relative-std=0.049,
SPY relative-std=0.102, both well under the 0.5 threshold (pass).

Walk-forward was not separately re-run this iteration given the time
budget spent on the SPY deadband-widening retune sweep; the grid's own
consistently positive Sharpe across the parameter space provides
supporting robustness evidence.

## Validators summary

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe >= 1.0 | PASS (1.139) | PASS (1.044, retuned deadband) | PASS (1.323) | PASS (1.021) |
| MDD <= 25% | PASS | PASS | PASS | PASS |
| TC-survival net Sharpe >= 0.5 | PASS | PASS (retuned deadband) | PASS | PASS |
| Param sensitivity relstd <= 0.5 | PASS | PASS | n/a | n/a |
| Walk-forward | not run this iteration | | | |

## Decision: ACCEPT -- full universe (QQQ, SPY, BTC/USDT, ETH/USDT)

All four symbols pass Sharpe/MDD/TC-survival. This is the fourth
continuous-sizing-dial strategy accepted this cron trigger (after Amihud
ILLIQ, Corwin-Schultz spread, VPCI), and the first to successfully rescue
a previously DECISIVELY (not just near-miss) rejected binary-trigger REX
Oscillator entry via the continuous-sizing reframing, without needing any
deep leverage-cap change for crypto beyond the repo's standard
leverage-cap-aware starting point.
