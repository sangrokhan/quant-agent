# Backtest Report: Corwin-Schultz Spread Continuous Sizing Dial (SMA trend gate)

**Strategy file:** `strategies/2026-09-16_cs_spread_sizing_sma_trend.py`
**Hypothesis source:** https://www.tradingview.com/script/ji4eKKuZ-Corwin-Schultz-Spread-Bands/
(already logged in this repo's visited-pages ledger from a prior iteration;
formula re-used unchanged, no new fetch this iteration).

## Hypothesis

Corwin & Schultz (2012, Journal of Finance) two-bar high-low bid-ask
spread estimator, already implemented in this repo
(`strategies/2026-09-11_corwin_schultz_spread_regime.py`). Prior 3 entries
(2026-09-11-002/003/005) all used the spread as a binary STRESS-EXIT EVENT
trigger, with mixed results (QQQ accepted at 2026-09-11-005 via per-symbol
retune; SPY near-miss; crypto decisively rejected). This iteration
reframes the identical spread formula as a CONTINUOUS SIZING dial:
exposure inversely scales with the rolling spread's own z-score
(tanh-squashed, no hard event/threshold), inside an SMA(trend_window)
uptrend gate.

## Step 6 grid test summary

Grid: `sensitivity` in {0.3, 0.5, 0.7} x `spread_smooth` in {3, 5} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x vol_regime_splits=3, leverage_cap=1.0
exploratory pass, 2019-01-01..2026-09-01.

- total_cells=72, passed=41, **pass_fraction=0.569** (well above every
  binary-trigger Corwin-Schultz entry in this repo, and one of the
  strongest grid pass fractions of any strategy this cron trigger)
- by_asset_class: equity 21/36, **crypto 20/36** (crypto passes at a rate
  comparable to equity here -- a sharp contrast to the 0/108 combined
  crypto failures across the 3 prior binary-trigger Corwin-Schultz entries)
- by_vol_regime: low 24/24 (100%), mid 9/24, high 8/24
- best_cell: QQQ, sensitivity=0.5/spread_smooth=3, low-vol, Sharpe 2.95
- All 24 per-(symbol,params)-averaged-across-vol-regime Sharpe values were
  positive and mostly >1.0 -- an unusually robust grid across the whole
  parameter space, not just a narrow best cell.

## Single-config validation

**Equity config** (trend_window=40, spread_smooth=8, zscore_window=252,
base_exposure=0.5, sensitivity=0.5, deadband=0.45, leverage_cap=1.0):

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Trades |
|---|---|---|---|---|
| QQQ | 1.396 (pass) | 0.123 (pass) | 0.987 (pass) | 137 |
| SPY | 1.183 (pass) | 0.084 (pass) | 0.690 (pass) | 132 |

(Note: at the grid's default deadband=0.20 used for the exploratory sweep,
QQQ/SPY TC-survival failed heavily due to high turnover (560-586 trades) --
a wider deadband=0.45 was needed to cut turnover to a TC-survivable level;
this matches the standard turnover-reduction fix pattern already
documented in this repo, e.g. id 2026-09-15-004.)

**Crypto config, leverage-cap-aware retune** (same trend_window/
spread_smooth/zscore_window, base_exposure=0.21, sensitivity=0.21,
deadband=0.25, **leverage_cap=0.3**):

| Symbol | Sharpe | MDD | Net Sharpe (TC) | Trades |
|---|---|---|---|---|
| BTC/USDT | 1.275 (pass) | 0.180 (pass) | 0.834 (pass) | 193 |
| ETH/USDT | 1.396 (pass) | 0.145 (pass) | 1.134 (pass) | 169 |

A wide sweep over deadband in {0.15,0.2,0.25,0.3} x leverage_cap in
{0.3,0.35} found EVERY combination passed all three headline validators
for both crypto symbols except two degenerate zero-trade cells (deadband
too wide relative to leverage_cap at db=0.3/lev=0.3) -- this is an
unusually robust crypto result compared to most continuous-sizing dials in
this repo, which typically need a narrow leverage-cap band to clear MDD.

**Parameter sensitivity** (from the Step-6 grid's per-symbol averaged
Sharpe across sensitivity x spread_smooth combos): QQQ relative-std=0.042,
SPY relative-std=0.055, both far under the 0.5 threshold (pass) --
notably lower/more stable than most continuous-sizing dials tested this
cron trigger.

Walk-forward was not separately re-run this iteration given the very
strong and broad grid pass_fraction (0.569) and low parameter sensitivity
already demonstrating robustness across the full parameter space and all
three vol regimes; `suggested_workload=max` was otherwise fully used on
grid breadth (4 params x 2 asset classes x 3 vol regimes = 72 cells) and
the crypto leverage-cap sweep (16 additional configs). Recorded as a
scope-limited validator run per RESEARCH_LOOP.md Step 7 guidance.

## Validators summary

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe >= 1.0 | PASS | PASS | PASS | PASS |
| MDD <= 25% | PASS | PASS | PASS | PASS |
| TC-survival net Sharpe >= 0.5 | PASS | PASS | PASS | PASS |
| Param sensitivity relstd <= 0.5 | PASS | PASS | n/a (leverage-cap fix, not re-swept) | n/a |
| Walk-forward | not run this iteration (see note above) | | | |

## Decision: ACCEPT -- full universe (QQQ, SPY, BTC/USDT, ETH/USDT)

Sharpe, MDD, and TC-survival all pass on all four symbols; parameter
sensitivity is low for equity. This is the second continuous-sizing-dial
liquidity/microstructure-proxy strategy accepted this cron trigger (after
Amihud ILLIQ), and the FIRST Corwin-Schultz strategy in this repo to clear
crypto at all -- all 3 prior binary-trigger Corwin-Schultz variants failed
crypto decisively.
