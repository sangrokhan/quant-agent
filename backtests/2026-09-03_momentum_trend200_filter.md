# Backtest Report — 2026-09-03_momentum_trend200_filter

**Hypothesis:** Long-term (200-day) SMA trend filter ANDed with a
medium-term (30-90d) absolute-momentum signal reduces max drawdown enough
to clear the 35% hard risk budget on BTC/USDT and SPY/QQQ, addressing the
MDD failures of prior pure-momentum attempts (2026-09-03-002: 90d lookback,
MDD 66.0%; 2026-09-03-003: 45d lookback + vol-target overlay, MDD 47.6%).

**Source:** https://github.com/IsaacDodds/crypto-momentum-backtest (README).
That backtest found a 200-day BTC trend filter roughly halved max drawdown
on a cross-sectional crypto momentum strategy (v1 unfiltered MDD -89.8% ->
v2 filtered MDD -53.8%), at some Sharpe cost. This strategy tests the same
"long-horizon SMA gate" mechanism but as an AND-condition with a shorter
absolute-momentum signal, on single-asset BTC/USDT and equity (SPY/QQQ) —
the source only tested a cross-sectional crypto universe.

**Universe / period:** SPY, QQQ (equity, `load_equity`), BTC/USDT, ETH/USDT
(crypto, `load_crypto` daily bars), 2019-01-01 to 2026-09-01.

**Signal:** long when `close[t] > SMA(trend_window)` AND
`close[t]/close[t-mom_window] - 1 > 0`; flat otherwise. Position lagged 1
day to avoid look-ahead.

## Step 6 — Grid test (mom_window ∈ {30,60,90} × trend_window ∈ {150,200} ×
2 equity + 2 crypto symbols × 3 vol-regime terciles = 72 cells)

- **Overall pass_fraction: 0.403** (29/72 cells pass Sharpe>=1.0 AND MDD<=35%)
- By asset class: equity 18/36 (50%), crypto 11/36 (30.6%)
- By vol regime: low 20/24 (83%), mid 8/24 (33%), high 1/24 (4%)
- Best cell: SPY, mom_window=30, trend_window=200, low-vol regime, Sharpe 2.86
- Worst cell: QQQ, mom_window=60, trend_window=150, high-vol regime, Sharpe -0.50

Clear pattern: the trend filter works well in low-vol regimes but breaks
down in mid/high-vol regimes (same failure mode flagged in
2026-09-01-001's rejection notes) — trend filters lag in choppy/high-vol
markets and the 1-day-lagged binary position still gets whipsawed.

## Step 7 — Single-config validation (best cell params: mom_window=30,
trend_window=200), full-sample, both asset classes

| Symbol | Sharpe | MDD | TC-adj Sharpe | Param sensitivity (rel.std) |
|---|---|---|---|---|
| SPY | 0.94 (FAIL, need >=1.0) | 15.9% (PASS, <=35%) | 0.69 (PASS, >=0.5) | 0.12 (PASS, <=0.5) |
| BTC/USDT | 1.10 (PASS) | 37.0% (FAIL, <=35%) | 1.04 (PASS) | 0.05 (PASS) |

Full-sample single-config performance is a materially harder bar than the
best grid cell (which is cherry-picked to a specific low-vol tercile) — as
expected, the full-sample numbers are worse than the "best_cell" headline.

## Decision: REJECT

Neither tested full-sample asset survives all validators at the
grid-optimal config: SPY misses the Sharpe threshold (0.94 vs 1.0, narrow
miss), and BTC/USDT narrowly exceeds the max-drawdown budget (37.0% vs
35.0%, a ~2pp overshoot — much closer than the prior two BTC momentum
attempts but still a hard-gate fail). Transaction-cost survival and
parameter sensitivity pass comfortably for both. Grid pass_fraction 40% is
regime-dependent (works well in low-vol, fails in mid/high-vol) — consistent
with the source material's own honest caveat that a long-horizon trend
filter is a drawdown *control*, not a reliable alpha source, and doesn't
uniformly clear this repo's risk gates across full samples.

## Notes for future loops

- This is the closest any BTC momentum variant has gotten to clearing MDD
  (37.0% vs 2026-09-03-002's 66.0% and 2026-09-03-003's 47.6%) — the
  200d trend filter mechanism is directionally the right lever. A future
  loop could try: (a) a slightly longer trend_window (250-300d) to further
  reduce whipsaws, (b) combining the trend filter with the vol-targeting
  overlay from 2026-09-03-003 rather than either alone, or (c) an explicit
  stop-loss/ATR trailing-stop exit (a distinct mechanism suggested by
  search results this iteration but not extractable — see visited_pages.jsonl,
  quantifiedstrategies.com and pyquantlab Medium post were both blocked by
  bot-verification/Cloudflare and yielded no usable content).
- Equity (SPY) full-sample Sharpe (0.94) is very close to threshold —
  a coarser trend_window or adding a QQQ leg might tip it over 1.0; not
  pursued further this iteration to keep scope tight per `normal` workload.
