# Backtest Report: Jump-Weighted Momentum (magnitude-weighted formation returns)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_jump_weighted_momentum.py`
**Source:** Beckmeyer & Wiedemann, "All Days Are Not Created Equal:
Understanding Momentum by Learning to Weight Past Returns" (Journal of
Banking & Finance, 2025), https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5702162
(SSRN page itself blocked by Cloudflare bot check via browser_exec; summary
obtained from Google's AI overview of the SSRN/ScienceDirect abstract text,
surfaced from Quantpedia's April 2026 monthly digest
https://quantpedia.com/quantpedia-in-april-2026 listing it as a 2026 Awards
finalist paper).

## Hypothesis

The paper's learned "Characteristic-Managed Momentum" (CMM) model finds that
standard equal-weighted 12-1 momentum wastes most of the formation window on
noise: on average ~2 days receive ~30% of the total learned weight and ~30
days account for over half the weight, concentrated on informative-event
days (earnings, jumps, large moves). CMM achieves Sharpe 0.77 net of costs
with much lower volatility (12.6% vs 26.9% for standard momentum).

Adapted here (no cross-sectional universe / earnings dates in this repo) as
a single-asset time-series momentum score that weights each day's return in
the formation window by its own realized magnitude: `w_t = |r_t|^jump_power`,
score = weighted-average return over the trailing `lookback_days` (excluding
the most recent `skip_days`). Long when score > 0, flat otherwise, lagged
1 day.

Distinct from other momentum variants in this repo: plain 12-month TSMOM
(2026-09-03-012) and the multiplicative reversal-tilt B=(1+r)*M
(2026-09-08-144, rejected) both equal-weight the formation window itself;
none reweight individual days by realized |return| magnitude.

## Grid test (Step 6)

`param_grid={lookback_days: [63,126,252], jump_power: [0.0,1.0,2.0]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3` (108 cells total).

- **pass_fraction: 0.269** (29/108)
- **by_asset_class:** equity 29/54 passed; crypto **0/54** (decisive reject on crypto)
- **by_vol_regime:** low 18/36, mid 5/36, high 6/36 — edge concentrated in low-vol, but QQQ/SPY at jump_power=2.0 clear ALL THREE vol regimes at lookback_days=126 and 252 (full-regime robustness, not just low-vol).
- **best_cell:** QQQ, lookback_days=63, jump_power=1.0, low-vol, Sharpe 2.85
- Best full-regime-robust cell: **QQQ lookback_days=126, jump_power=2.0** — passed low (Sharpe 1.58), mid (1.24), high (1.03) all three; **QQQ lookback_days=252, jump_power=2.0** also 3/3.

## Single-config validation (Step 7): lookback_days=126, jump_power=2.0, skip_days=5

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.232 (PASS) | 1.536 (PASS) | >= 1.0 |
| Max drawdown | 0.207 (PASS) | 0.111 (PASS) | <= 0.25 |
| TC survival (5bps/trade) | 1.192 (PASS, 53 trades) | 1.493 (PASS, 39 trades) | >= 0.5 |
| Walk-forward (4 manual chunks, vbt.utils.splitting AttributeError workaround) | 0.75 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity (9-combo local grid, lookback_days in [100,126,150] x jump_power in [1.5,2.0,2.5]) | relative_std 0.160 (PASS) | relative_std 0.092 (PASS) | <= 0.5 |

## Decision: **ACCEPT (QQQ + SPY, lookback_days=126, jump_power=2.0, skip_days=5)**

Both QQQ and SPY clear every validator at full-sample level; crypto
(BTC/USDT, ETH/USDT) rejected decisively (0/54 grid cells) and is out of
scope for this strategy. Notably robust across all three volatility
regimes for this specific config (jump_power=2.0), not just a narrow slice.
