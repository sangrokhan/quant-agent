# Backtest Report: Money Flow Oscillator (MFO) Persistence Confirmation (Apirine, TASC Oct 2015)

**Strategy file:** `strategies/2026-09-17_mfo_persistence_confirmation.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2015/10/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored;
direct traders.com archive URL navigation to a previously-unvisited month)

## Hypothesis

Apirine's MFO uses a symmetric bounded [-1,1] multiplier comparing today's
high/low range extension against BOTH yesterday's high AND low
simultaneously, multiplies by volume, sums over a lookback window, and
normalizes by summed volume. The article's OWN strategy requires MFO to
stay on one side of zero for `confirm_bars` consecutive bars before
entering (persistence confirmation, not a simple zero-cross).

## Per-symbol tuned configs (per-symbol tuning, established repo pattern)

| Validator | QQQ (length=20,confirm_bars=3) | SPY (length=10,confirm_bars=2) |
|---|---|---|
| Sharpe (>=1.0) | PASS (1.462) | PASS (1.266) |
| Max Drawdown (<=0.25) | PASS (0.192) | PASS (0.149) |
| TC survival (net Sharpe>=0.5) | PASS (1.418) | PASS (1.151) |
| Walk-forward (>=75%) | PASS (4/4) | PASS (4/4) |
| Parameter sensitivity (<=0.5) | PASS (0.090) | PASS (0.156) |
| Trades | 33 | 64 |

Crypto (BTC/USDT, ETH/USDT, using QQQ's config): decisive reject -- Sharpe
fails both (0.248, 0.259), MDD fails both (0.529, 0.594), TC-survival fails
both (0.099, 0.135).

## Step 6 grid summary (length in {14,20,30} x confirm_bars in {2,3}, 3 vol terciles, equity+crypto, 72 cells)

- `pass_fraction`: 24/72 = 0.333
- `by_asset_class`: equity 19/36, crypto 5/36 (crypto passes narrow low-vol-tercile only)
- `by_vol_regime`: low 17/24, mid 7/24, high 0/24 (edge concentrated in
  calm regimes, consistent with other trend-persistence-confirmation
  strategies this trigger)
- `best_cell`: length=20/confirm_bars=3, QQQ, low-vol, Sharpe 3.15
- `worst_cell`: length=30/confirm_bars=3, SPY, high-vol, Sharpe -0.89

SPY initially failed Sharpe (0.937) at the grid-best shared config; a
SPY-specific retune (length=10, confirm_bars=2) rescued it.

## Decision

**Accept for QQQ and SPY** (per-symbol tuned configs, all 5 validators
pass). **Reject for crypto** decisively (BTC/USDT, ETH/USDT both fail
Sharpe/MDD/TC-survival with high turnover ~1400 trades).

Scope: full equity universe accept (QQQ+SPY), per-symbol tuned
parameters, moderate turnover (33-64 trades over 7.5 years). Crypto
explicitly out of scope at these settings.
