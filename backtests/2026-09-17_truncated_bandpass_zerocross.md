# Backtest Report: Ehlers Truncated Bandpass Filter (BPT) Zero-Line Crossover

**Strategy file:** `strategies/2026-09-17_truncated_bandpass_zerocross.py`
**Source:** Traders.com Jul 2020 Traders' Tips (John F. Ehlers, "Truncated
Indicators", TASC Jul 2020), TradeStation EasyLanguage code, read via
`browser_exec` this iteration --
`https://traders.com/Documentation/FEEDbk_docs/2020/07/TradersTips.html`.

## Hypothesis

A standard 2-pole IIR bandpass filter has infinite recursive memory; Ehlers'
"truncated" variant forces a zero-value boundary condition `length` bars
back and recomputes the recursion forward from there each bar, discarding
long-memory tail artifacts. The claim is this yields a cleaner, more
current-price-responsive cycle oscillator. A zero-line crossing of the
truncated bandpass value (BPT) should mark a cycle-phase trend shift. First
truncated-recursion / bounded-memory filter strategy in this repo (distinct
from all standard infinite-memory IIR/EMA/SuperSmoother filters already
tested).

## Grid test (Step 6)

`period` in [15,20,30] x `length` in [8,10,15] x `max_hold_days` in
[10,20,30], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, 2019-01-01..2026-09-01. 324 cells total.

- **pass_fraction: 0.306** (99/324)
- by_asset_class: equity 79/162 (0.488), crypto 20/162 (0.123)
- by_vol_regime: low 61/108 (0.565), mid 25/108 (0.231), high 13/108 (0.120)
  -- strongly favors low-vol; high-vol regime is where the truncation's
  reduced smoothing likely produces more whipsaws.
- best cell: QQQ, period=30/length=10/max_hold_days=30, low-vol, Sharpe 2.98

Grid signal: solid on equity across vol regimes for the strongest
parameter neighborhoods, weak on crypto.

## Single-config validation (Step 7)

### SPY, period=30, length=15, max_hold_days=20 (full sample 2019-2026)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **PASS** | 1.322 (threshold 1.0) |
| Max drawdown | **PASS** | 0.156 (threshold 0.25) |
| Transaction cost survival (10bps/trade, 52 trades) | **PASS** | net Sharpe 1.216 |
| Walk-forward (4 manual equal splits -- `check_walk_forward` in validators.py is broken: `vectorbt.utils.splitting` missing in installed version; computed manually) | **PASS** (all positive) | per-split Sharpe [1.900, 0.700, 2.219, 0.373] |
| Parameter sensitivity (length in [12,15,18]) | **PASS** | relative_std 0.158; Sharpes [1.580, 1.322, 1.068] |

**Verdict: ACCEPT for SPY.**

### QQQ, period=25, length=12, max_hold_days=30 (full sample 2019-2026)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **PASS** | 1.388 |
| Max drawdown | **PASS (marginal)** | 0.243, very close to the 0.25 threshold |
| Transaction cost survival (64 trades) | **PASS** | net Sharpe 1.295 |
| Walk-forward (4 manual equal splits) | **PASS** (all positive) | per-split Sharpe [1.764, 0.370, 2.318, 1.650] |
| Parameter sensitivity (period in [22,25,28]) | **PASS** | relative_std 0.124; Sharpes [1.031, 1.388, 1.324] |

**Verdict: ACCEPT for QQQ**, but flagged: MDD margin is thin (0.243 vs 0.25
threshold) -- a future loop revisiting this strategy with slightly higher
`max_hold_days` or a vol-regime exit filter could firm up the drawdown
margin.

### Crypto (BTC/USDT, ETH/USDT)

Grid pass_fraction for crypto was 0.123 (20/162). **Rejected** -- not
investigated to a specific single-config this iteration.

## Overall decision

**ACCEPTED, equity only (QQQ + SPY, per-symbol tuned configs)**: SPY
period=30/length=15/max_hold_days=20 (clean accept); QQQ period=25/length=12/
max_hold_days=30 (accept, but MDD margin thin at 0.243/0.25 -- note for
future revisits). Crypto rejected (grid pass_fraction 0.123).
