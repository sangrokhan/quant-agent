# 2026-09-10 — Frog-in-the-Pan (FIP) Information Discreteness Continuation Filter

## Hypothesis

Per Da, Gurun & Warachka, "Frog in the Pan: Continuous Information and
Momentum" (SSRN working paper, Nov 2011; formula per
https://business.uq.edu.au/sites/default/files/events/files/mitch-warachka-paper.pdf,
equation 1): momentum/trend continuation is empirically stronger when a
stock's formation-period return is built from many small same-signed daily
moves ("continuous information", low ID) rather than a few large jumps
("discrete information", high ID). ID = sign(PRET) * (%neg - %pos). Paper's
own cross-sectional finding (Table 2): 6-month unadjusted momentum increases
monotonically from 2.91% (discrete-info quintile) to 8.86% (continuous-info
quintile), t-stat 5.13.

Adapted to a single-asset time-series filter (this repo's loaders provide
single-symbol OHLCV only, not a cross-sectional equity universe): stay long
only while (1) trailing-formation-period return (PRET, 189-day lookback
skipping the most recent 5 days) is positive, AND (2) that trend's own ID
reading is at/below a threshold (continuous, i.e. built from steady small
up-days rather than a few big jumps). Exit when either condition breaks, or
a 60-day time-stop safety backstop.

Source: https://business.uq.edu.au/sites/default/files/events/files/mitch-warachka-paper.pdf
(full academic PDF, exact ID formula equation 1 disclosed and used verbatim).

## Best config (from grid)

`lookback_days=189, id_threshold=0.0, skip_days=5, max_hold_days=60`

## Single-config validator results (equity, full 2019-01-01..2026-09-01 sample)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.850 (FAIL, thr 1.0) | 0.286 (FAIL, thr 0.25) | 0.820 (PASS, thr 0.5) | 0.75 (PASS, thr 0.75) | 0.093 (PASS, thr 0.5) |
| SPY | 0.635 (FAIL, thr 1.0) | 0.311 (FAIL, thr 0.25) | 0.601 (PASS, thr 0.5) | 0.50 (FAIL, thr 0.75) | 0.066 (PASS, thr 0.5) |

Both symbols decisively fail full-sample Sharpe and max-drawdown; SPY also
fails walk-forward. Parameter sensitivity is low (the strategy is stable
across nearby lookback/threshold values — it's just not a good strategy at
any of them).

## Grid-test summary (`validation/grid_test.py`)

Grid: `lookback_days in [126, 189, 252]` x `id_threshold in [-0.02, -0.05, 0.0]`
x symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}` x
`vol_regime_splits=3` (low/mid/high realized-vol terciles), 2019-01-01 to
2026-09-01.

- **Total cells: 108, passed: 19, pass_fraction: 0.176**
- By asset class: equity 19/54 passed; **crypto 0/54 passed** (decisive
  reject on crypto).
- By vol regime: low-vol 18/36 passed; mid-vol 1/36; **high-vol 0/36** — the
  strategy's apparent edge is almost entirely a low-volatility-regime
  artifact (consistent with many prior trend-following strategies in this
  repo failing to generalize across vol regimes).
- Best cell: SPY, low-vol regime, `lookback_days=189, id_threshold=0.0`,
  Sharpe 2.87 (this is the cherry-picked best of 108 cells, not
  representative of the full-sample result above).
- Worst cell: SPY, mid-vol regime, `lookback_days=126, id_threshold=-0.05`,
  Sharpe -0.37.

## Decision: REJECTED

All full-sample validators for QQQ and SPY fail (Sharpe below 1.0, MDD above
25%); grid pass_fraction of 0.176 is low and concentrated almost entirely in
the low-vol tercile. Crypto shows zero passing cells across the entire grid.
The paper's own cross-sectional equity-factor result does not survive
adaptation into a single-asset time-series filter at any tested parameter
combination.

`strategies/2026-09-10_fip_information_discreteness.py` is kept as a record
of a rejected attempt — do not treat it as a live strategy.
