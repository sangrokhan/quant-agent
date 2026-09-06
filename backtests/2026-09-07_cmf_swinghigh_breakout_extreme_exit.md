# CMF Zero-Cross + Swing-High Breakout, Extreme-Reading Curl-Back Exit

**Hypothesis:** Per https://theindicatorlab.com/reviews/chaikin-money-flow-cmf/
(source's own disclosed best-tested strategy): long entry when CMF(20)
crosses above zero from the "indecision zone" (|CMF|<=0.05) AND price closes
above a recent swing high; exit when CMF reaches an extreme reading (+0.25)
and curls back down, or safety-exits on a cross back below zero or a
max_hold_days time-stop.

Source: https://theindicatorlab.com/reviews/chaikin-money-flow-cmf/.
Distinct from this repo's existing CMF strategy
(2026-09-04_cmf_threshold_trend_filter.py, SMA trend filter + cross-below-zero
exit) via its swing-high breakout entry confirmation and extreme-reading
curl-back exit.

## Step 6 — Grid test (swing_lookback in {10,20,30}, extreme_threshold in
{0.20,0.25,0.30}, equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}, 1h bars,
vol_regime_splits=3, 2019-01-01 to 2026-09-01)

- Total cells: 108, passed: 18, **pass_fraction = 0.167**
- By asset class: equity 18/54 passed, **crypto 0/54 passed** (decisive fail)
- By vol regime: low 9/36, mid 9/36, high 0/36
- Best cell: QQQ, swing_lookback=10, extreme_threshold=0.30, low-vol regime,
  Sharpe 1.683
- Worst cell: QQQ, swing_lookback=30, extreme_threshold=0.25, high-vol
  regime, Sharpe -0.293

## Step 7 — Single-config validators (swing_lookback=10, extreme_threshold=0.30,
cmf_window=20 default, full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL (near-miss) 0.984 | FAIL (decisive) 0.325 |
| Max Drawdown (<= 0.25) | PASS 0.124 | PASS 0.080 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | PASS 0.811 (60 trades) | FAIL 0.143 (58 trades) |
| Parameter sensitivity (relative_std <= 0.5, swing_lookback {10,20,30} sweep, QQQ) | PASS 0.177 | PASS 0.177 |

Walk-forward not run: pre-existing `vbt.utils.splitting` AttributeError bug
in this repo's installed vectorbt version (same known issue as other recent
entries).

## Outcome: **REJECTED**

QQQ Sharpe is a near-miss (0.984 vs 1.0) but SPY fails decisively (0.325),
and SPY's transaction-cost survival check fails outright (0.143 vs 0.5
threshold at 58 trades) — the strategy's frequent breakout entries generate
enough trades that costs materially erode already-thin edge on SPY. Crypto
is a decisive 0/54 fail across the whole grid. Not accepted for any symbol;
the swing-high breakout confirmation on top of a CMF zero-cross does not
produce a robust enough edge net of costs.
