# Multi-Day Internal Bar Strength (IBS) Mean Reversion, Trend-Gated (QQQ) — REJECTED (parameter sensitivity)

**Hypothesis:** Internal Bar Strength IBS = (close-low)/(high-low)*100
measures where a bar closes within its own range; low IBS predicts
next-bar mean reversion higher (per Cesar Alvarez/Alvarez Quant Trading's
bucket-test research: IBS<25 keeps 63% of a base mean-reversion strategy's
trades with a 21% avg P/L improvement). Alvarez notes single-day IBS alone
hasn't worked well standalone in his own testing and suggests (untested by
him) averaging IBS over N days as an extension — this strategy implements
exactly that: N-day averaged IBS crossing below an oversold threshold,
gated by close > 200d SMA (uptrend, buying dips not falling knives).

**Source:** https://alvarezquanttrading.com/blog/internal-bar-strength/

**Novelty:** First IBS-family strategy in this repo. Distinct from every
prior mean-reversion strategy (Bollinger, RSI(2), Connors RSI, z-score)
since IBS uses the bar's own high/low range rather than a rolling-window
statistic.

## Best config: ibs_window=2, entry_threshold=25.0, exit_threshold=60.0, trend_window=200, max_hold_days=10 (QQQ, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.247 | >= 1.0 | PASS |
| Max drawdown | 7.67% | <= 25% | PASS |
| Transaction cost survival (5bps/trade, 144 trades) | net Sharpe 1.034 | >= 0.5 | PASS |
| Parameter sensitivity (relative std across ibs_window x entry_threshold, QQQ) | 0.606 | <= 0.5 | **FAIL** |
| Walk-forward | SKIPPED | n/a | Repo-wide `vectorbt.utils.splitting` API issue, see 2026-09-04-154 |

Per-config full-sample Sharpe grid (QQQ): iw2/et20=0.75, iw2/et25=1.25,
iw2/et30=1.35, iw3/et20=0.29, iw3/et25=0.79, iw3/et30=1.36, iw5/et20=0.02,
iw5/et25=0.32, iw5/et30=0.70. Sharpe scales strongly with BOTH a shorter
IBS window and a higher entry threshold — a fairly monotonic relationship,
but one that swings from near-zero (iw5/et20=0.02) to a strong 1.36
(iw3/et30) just from parameter choice, which is exactly the fragility
the sensitivity check is designed to catch.

## Step 6 grid summary (ibs_window in [2,3,5] x entry_threshold in [20,25,30], symbols QQQ/SPY equity + BTC/ETH crypto, vol_regime_splits=3)

- **Overall pass_fraction: 16.7%** (18/108 cells)
- **By asset class:** equity 18/54 (33.3%); crypto 0/54 (0%) — no edge on crypto at all.
- **By vol regime:** low 13/36 (36.1%), mid 2/36 (5.6%), high 3/36 (8.3%) — strongly concentrated in low-vol/calm conditions, weak elsewhere.
- **Best cell:** QQQ, ibs_window=2, entry_threshold=25.0, PASSES ALL 3 vol regimes (the only (symbol,param) combo in this grid to do so).
- SPY only reaches 2/3 regimes at its best config (ibs_window=3, entry_threshold=30.0).

## Decision: REJECT (parameter sensitivity)

The best QQQ config clears Sharpe, max drawdown, and transaction-cost
survival cleanly, and is the only (symbol, param) combination in the grid
to pass all 3 volatility regimes. However the full parameter-sensitivity
check fails (relative std 0.606 vs 0.5 max) — Sharpe swings from
essentially zero to a strong 1.36 across nearby parameter choices in the
grid, indicating the strategy's apparent edge is fragile to the specific
(ibs_window, entry_threshold) pair chosen rather than robust across a
neighborhood of reasonable settings. Per this repo's strict "all
validators must pass" acceptance rule, rejecting despite the single-config
result looking attractive. A future loop could revisit with a coarser,
more conservative default (e.g. ibs_window=3, entry_threshold=25-30, which
cluster more tightly around 0.8-1.4) and re-run parameter sensitivity on a
narrower, more defensible grid before re-attempting.
