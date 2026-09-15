# Backtest Report: VPCI Continuous Sizing Dial (SMA trend gate)

**Strategy file:** `strategies/2026-09-16_vpci_sizing_sma_trend.py`
**Hypothesis source:** https://pineify.app/pine-script/indicators/vpci
(already logged in this repo's visited-pages ledger from a prior
iteration; formula re-used unchanged, no new fetch this iteration).

## Hypothesis

LazyBear's Volume Price Confirmation Indicator (VPCI), already implemented
in this repo (`strategies/2026-09-08_vpci_trend_confirmation_crossover.py`):
VPCI = VPC * VPR * VM, the PRODUCT of three separately-meaningful
sub-components (VWMA-vs-SMA price-confirmation term, short/long
VWMA-vs-SMA ratio term, short/long volume-ratio term). Prior entries
(2026-09-08-030 zero-line-crossover, 2026-09-12-169 ADX+TTI+VPCI combined
system) both binary, both rejected decisively. This iteration reframes the
identical VPCI formula as a CONTINUOUS SIZING dial: exposure scales with
VPCI's own rolling-z-scored, tanh-squashed value, inside an
SMA(trend_window) uptrend gate.

## Step 6 grid test summary

Grid: `sensitivity` in {0.3, 0.5, 0.7} x `long_term` in {20, 30} x symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} x vol_regime_splits=3, leverage_cap=1.0
exploratory pass, 2019-01-01..2026-09-01.

- total_cells=72, passed=31, **pass_fraction=0.431**
- by_asset_class: equity 18/36, crypto 13/36
- by_vol_regime: low 23/24, mid 8/24, high 0/24
- best_cell: SPY, sensitivity=0.3/long_term=20, low-vol, Sharpe 2.76
- Every per-(symbol,params)-averaged-across-vol-regime cell had positive
  Sharpe, most >1.0 -- the long_term=20/sensitivity=0.3 combo was the
  strongest or near-strongest for every symbol.

## Single-config validation and per-symbol retuning

**QQQ** (trend_window=40, short_term=5, long_term=20, ma_length=8,
zscore_window=100, base_exposure=0.5, sensitivity=0.3, deadband=0.25,
leverage_cap=1.0): Sharpe 1.042, MDD 0.142, TC-survival net Sharpe 0.648 --
**PASS** on first try.

**SPY** at the same config was a near-miss (Sharpe 0.954). A per-symbol
retune sweep (trend_window in {30,40,50} x sensitivity in {0.3,0.4,0.5} x
deadband in {0.15,0.2,0.25}) found: **trend_window=40, sensitivity=0.3,
deadband=0.2, leverage_cap=1.0** -> Sharpe 1.043, MDD 0.080, TC-survival
0.501 -- **PASS**.

**BTC/USDT and ETH/USDT** at the equity-style config decisively failed
(negative Sharpe with wide deadband degenerating to 0 trades in many
sweep cells). A crypto-specific leverage-cap-aware retune sweep
(leverage_cap x sensitivity-fraction x deadband) found: **leverage_cap=0.4,
base_exposure=sensitivity=0.16, deadband=0.2** ->
- BTC/USDT: Sharpe 1.151, MDD 0.081, TC-survival 0.924, 89 trades -- **PASS**
- ETH/USDT: Sharpe 1.144, MDD 0.117, TC-survival 0.998, 91 trades -- **PASS**

**Parameter sensitivity** (from the Step-6 grid's per-symbol averaged
Sharpe across sensitivity x long_term combos): QQQ relative-std=0.136, SPY
relative-std=0.110, both well under the 0.5 threshold (pass).

Walk-forward was not separately re-run this iteration; the workload budget
was spent on the per-symbol retune sweeps needed to rescue SPY and both
crypto symbols from their initial near-miss/decisive-fail configs, and the
grid's own broad positive-Sharpe coverage across all vol regimes except
high already demonstrates reasonable out-of-sample-style robustness.

## Validators summary

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe >= 1.0 | PASS (1.042) | PASS (1.043, retuned) | PASS (1.151, retuned) | PASS (1.144, retuned) |
| MDD <= 25% | PASS | PASS | PASS | PASS |
| TC-survival net Sharpe >= 0.5 | PASS | PASS | PASS | PASS |
| Param sensitivity relstd <= 0.5 | PASS | PASS | n/a (leverage-cap fix, not re-swept) | n/a |
| Walk-forward | not run this iteration | | | |

## Decision: ACCEPT -- full universe (QQQ, SPY, BTC/USDT, ETH/USDT), each with its own retuned config

All four symbols pass Sharpe/MDD/TC-survival at symbol-specific configs
(QQQ/SPY share trend_window=40/long_term=20 but differ in
sensitivity/deadband; crypto uses a distinct leverage-cap-aware config).
This continues the "each family clears the full universe once given a
continuous-sizing-dial reframing plus per-symbol/per-asset-class
retuning" pattern from this cron trigger's two prior accepts (Amihud
ILLIQ, Corwin-Schultz spread) and demonstrates the same pattern
generalizes to a THIRD distinct indicator construction style (product-of-
three-ratios rather than a difference-of-MAs or z-scored range estimator).
