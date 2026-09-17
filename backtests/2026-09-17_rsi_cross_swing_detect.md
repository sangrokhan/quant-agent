# Backtest Report: RSI Cross Swing Detection (D'Errico TASC May 2017)

**Strategy file:** `strategies/2026-09-17_rsi_cross_swing_detect.py`
**Knowledge base id:** 2026-09-17-143
**Source:** https://traders.com/Documentation/FEEDbk_docs/2017/05/TradersTips.html
(D'Errico "Detecting Swings", TASC May 2017; TradeStation strategy shell,
RSI-cross swing method, read via browser_exec)

## Hypothesis

RSI(5) crossing up through 40 (source default `RSIOverSold`) signals a swing
low forming; exit unconditionally after 4 bars (source's own
`NumberOfBarsToExit` mechanic, its only exit condition for this method) —
long-only adaptation of the source's bidirectional shell, no trend filter.

## Step 6 — Grid test (rsi_length x entry_threshold x hold_bars, equity+crypto, 3 vol regimes)

Grid: `rsi_length in [3,5,8]`, `entry_threshold in [35,40,50]`, `hold_bars in
[3,4,6]`, symbols `equity=[QQQ,SPY]`, `crypto=[BTC/USDT,ETH/USDT]`, 3 vol
regime terciles, 2019-01-01 to 2026-09-01, 324 total cells.

- **Overall pass_fraction: 0.151** (49/324 cells: Sharpe>=1.0 AND MDD<=0.25)
- **by_asset_class:** equity 44/162 (0.272), crypto 5/162 (0.031)
- **by_vol_regime:** low 37/108 (0.343), mid 9/108 (0.083), high 3/108 (0.028)
- **Best cell:** rsi_length=8, entry_threshold=50, hold_bars=4, equity/SPY,
  low-vol regime, Sharpe=3.58
- **Best config overall (rsi_length=8, entry=50, hold_bars=4) per-cell breakdown:**
  QQQ low=1.67(pass)/mid=1.26(pass)/high=-0.40(fail);
  SPY low=3.58(pass)/mid=0.21(fail)/high=-0.32(fail);
  BTC low=0.05/mid=0.15/high=0.32 (all fail);
  ETH low=1.43(pass)/mid=0.04/high=-0.05(fail)

Same pattern seen repeatedly in this repo: edge concentrated in the low-vol
tercile only, decaying to near-zero or negative in mid/high vol.

## Step 7 — Single-config validators (best config: rsi_length=8, entry=50, hold_bars=4, full sample 2019-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.398 **FAIL** | 0.335 **FAIL** | >= 1.0 |
| Max drawdown | 0.385 **FAIL** | 0.297 **FAIL** | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.227 **FAIL** | 0.131 **FAIL** | >= 0.5 |
| Walk-forward (manual 4-fold, `check_walk_forward` broken under this env's vectorbt==1.1.0 — `vbt.utils.splitting` module doesn't exist) | 0.75 pass | 0.75 pass | >= 0.75 |
| Parameter sensitivity (relative std across 27-cell equity grid) | 0.818 **FAIL** | 0.620 **FAIL** | <= 0.5 |

Full-sample Sharpe (0.33-0.40) is far below the grid's best-cell low-vol-only
Sharpe (1.67-3.58) — confirming the grid finding that the edge is entirely a
low-vol-regime artifact, wiped out once mid/high-vol periods are included in
the full sample. 4 of 5 validators fail decisively.

## Step 8 — Decision: **REJECT**

Only walk-forward passes; Sharpe, MDD, transaction-cost, and parameter
sensitivity all fail on both QQQ and SPY full-sample. The strategy shows no
value beyond the already-documented low-vol-regime niche (which itself
didn't clear the grid's own regime-specific pass threshold with enough
margin/consistency to justify a narrower-scope accept, unlike e.g.
2026-09-17-140 ESD Bands). Strategy file kept in `strategies/` as a rejected-attempt
record (see knowledge_base notes).
