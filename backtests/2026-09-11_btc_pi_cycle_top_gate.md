# Backtest report: BTC/ETH Pi Cycle Top macro-cycle-top exit gate

**Strategy file:** `strategies/2026-09-11_btc_pi_cycle_top_gate.py`
**Hypothesis source:** lookintobitcoin.com / bitbo.io / ryder.id (Google
AI-overview synthesis, visited this iteration via browser_exec fallback --
web_search returned no usable results for this query on the DuckDuckGo
backend).

## Hypothesis

The Pi Cycle Top Indicator (111-day MA crossing above 2x the 350-day MA)
has historically coincided within ~3 days of Bitcoin's major bull-cycle
price peaks (2013, 2017, April 2021). Operationalized as a long/flat
overlay: hold BTC/ETH long (optionally gated by their own SMA
trend_sma_window trend filter), go FLAT whenever the Pi Cycle Top condition
is active, with an optional reentry_buffer_days cooldown. First BTC-specific
on-chain-MA-derived macro-cycle-timing signal in this repo.

## Grid test summary (Step 6)

`param_grid={"trend_sma_window": [0,100,150,200], "reentry_buffer_days": [0,10,20]}`,
`symbols={"equity": ["QQQ","SPY"] (falsification -- no BTC cycle-top analog expected), "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 144 total cells, 2018-01-01 to 2026-09-01.

- pass_fraction: 0.326 (47/144)
- by_asset_class: equity 36/72, crypto 11/72
- by_vol_regime: low 35/48, mid 12/48, high 0/48 -- edge (where present)
  concentrated in the low-vol tercile only, as with many prior near-miss
  strategies in this repo.
- best_cell: SPY, trend_sma_window=0/reentry=0, low-vol regime, Sharpe=2.598
  (equity trend-only baseline with no crypto-specific mechanism at play --
  not evidence for the Pi Cycle Top hypothesis itself).
- Crypto per-symbol-per-regime Sharpe pattern: BTC's best full grid-cell
  average was trend_sma_window=100 (low-vol 1.802, mid-vol 1.02); ETH's
  best was trend_sma_window=150 (low 1.977, mid 0.431/0.453) -- but the
  grid's vol-regime slicing does not capture full-sample drawdown risk,
  which is the decisive failure mode here (see below).

## Single-config validation (Step 7)

Full-sample (2018-01-01 to 2026-09-01) Sharpe / max drawdown, best grid
configs per symbol:

| Symbol | trend_sma_window | Sharpe | MDD |
|---|---|---|---|
| BTC/USDT | 100 | 0.978 | 0.556 |
| ETH/USDT | 150 | 0.996 | 0.519 |

- `check_sharpe_ratio`: marginal FAIL for both (0.978 and 0.996, both just
  under the 1.0 threshold).
- `check_max_drawdown`: **FAILED decisively** for both (0.556 and 0.519 vs
  0.25 budget) -- the Pi Cycle Top gate only protects against the specific
  historical blow-off-top pattern (3 occurrences in the full sample: 2013,
  2017, 2021) and does NOT protect against the much more frequent/severe
  ordinary bear-market drawdowns (2018, 2022) that dominate BTC/ETH's
  overall drawdown profile -- a narrow, rare-event circuit breaker cannot
  rescue a raw always-in-market trend strategy's baseline drawdown risk.
- `check_transaction_cost_survival`: **FAILED** for BTC (net Sharpe after
  a 10bps/trade cost collapses to 0.012 from a gross 0.978) -- the
  underlying SMA-trend-gated position (computed on hourly bars via the
  daily-resampled MA logic) generates far more position transitions than
  the ~3-per-cycle Pi Cycle Top signal itself, since the `trend_sma_window`
  gate dominates turnover.
- Walk-forward: attempted but `validation/validators.py`'s
  `check_walk_forward` raised an `AttributeError` (`vectorbt.utils` has no
  `splitting` attribute in the installed vectorbt version) -- this is a
  pre-existing environment/dependency issue with the validator itself, not
  specific to this strategy; not run given the decisive MDD/TC-survival
  failures already found via the two validators that did run successfully.

## Decision: REJECTED

Both BTC and ETH configurations fail max-drawdown decisively (0.52-0.56 vs
0.25 budget) and BTC additionally fails transaction-cost survival. The Pi
Cycle Top signal itself is a genuine, well-documented historical pattern
(rare blow-off-top MA crossovers), but as a risk-off overlay it only
addresses 3 specific historical events and does nothing to protect against
the far more common/severe ordinary crypto bear-market drawdowns that
dominate the full-sample risk profile -- the underlying always-in-market
(or SMA-trend-gated) base position is the actual drawdown driver, not
something this narrow circuit-breaker construction can fix.

## Notes for future loops

- The Pi Cycle Top signal ITSELF (not as an overlay, but isolated: what
  does the market do in the N days immediately following an active
  crossover) might be worth testing as a pure short-horizon reversal signal
  around the 3 known historical events, though the tiny sample size (n=3
  cycle tops in 2018-2026 data) would make any such backtest very
  low-power/high-variance -- flagging this as a lower-confidence follow-up
  idea rather than pursuing it this iteration.
- `validation/validators.py::check_walk_forward` throws an AttributeError
  against the currently installed vectorbt version (`vectorbt.utils` has no
  `splitting` submodule) -- worth a maintenance fix in a future loop since
  it silently blocks the walk-forward check for every strategy, not just
  this one.
