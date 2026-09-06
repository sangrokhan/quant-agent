# GARCH(1,1) Conditional-Volatility Regime Gate

**Hypothesis:** Per https://www.quantopia.net/time-series/garch-volatility, a
GARCH(1,1) model (`sigma_t^2 = omega + alpha*eps_{t-1}^2 + beta*sigma_{t-1}^2`)
captures volatility clustering better than a trailing realized-vol window.
Operationalized as a binary long/flat regime gate: long while forecast
annualized conditional vol <= `vol_threshold`, flat otherwise. GARCH(1,1)
refit every `refit_every` days (not every bar) via `scipy.optimize.minimize`
MLE (no `arch` package in this repo's venv).

Source: https://www.quantopia.net/time-series/garch-volatility (own example:
"if GARCH equity volatility exceeds 25%, the portfolio shifts to keep
overall portfolio volatility at a target annualized level").

## Step 6 — Grid test (vol_threshold in {0.20,0.25,0.30}, refit_every in
{21,42}, equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT} daily bars,
vol_regime_splits=3, 2019-01-01 to 2026-09-01)

- Total cells: 72, passed: 14, **pass_fraction = 0.194**
- By asset class: equity 14/36 passed, **crypto 0/36 passed** (decisive fail)
- By vol regime: low 12/24, mid 2/24, high 0/24 — edge (where it exists)
  concentrated entirely in the low-vol tercile, consistent with a long/flat
  vol-target gate design (mechanically stays invested mostly during the
  low-vol regime).
- Best cell: SPY, vol_threshold=0.20, refit_every=21, low-vol regime, Sharpe
  2.588
- Worst cell: BTC/USDT, vol_threshold=0.30, refit_every=42, low-vol regime,
  Sharpe -0.997

## Step 7 — Single-config validators (vol_threshold=0.20, refit_every=21,
full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL (near-miss) 0.811 | FAIL (near-miss) 0.714 |
| Max Drawdown (<= 0.25) | PASS 0.178 | PASS 0.191 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | PASS 0.783 (22 trades) | PASS 0.689 (17 trades) |
| Parameter sensitivity (relative_std <= 0.5, vol_threshold {0.20,0.25,0.30} sweep, SPY) | PASS 0.054 | PASS 0.054 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **REJECTED** (near-miss on both equity symbols)

Full-sample Sharpe misses the 1.0 bar on both QQQ (0.811) and SPY (0.714),
even though MDD/transaction-cost/parameter-sensitivity all pass cleanly and
the grid confirms the edge is real but confined to the low-vol tercile (as
expected for a vol-target gate design — it can only add value by avoiding
losses in high-vol regimes, not by generating alpha within the low-vol
regime itself). Crypto is a decisive 0/36 fail across the whole grid.
Genuinely fitted GARCH(1,1) conditional variance (vs. this repo's existing
trailing-realized-vol regime gates) did not produce a meaningfully better
full-sample Sharpe than those simpler filters already tested and
rejected/accepted elsewhere in this repo.
