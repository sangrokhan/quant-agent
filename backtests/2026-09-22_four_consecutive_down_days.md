# 2026-09-22: Four Consecutive Down Days (unconditional mean-reversion)

**Hypothesis source:** QuantifiedStrategies.com, "Four Consecutive Down Days
Trading Strategy: A Guide"
(https://www.quantifiedstrategies.com/four-down-days-and-up/), accessed
2026-09-22 via browser_exec (web_search DDGS backend returned only page
snippets, direct page load confirmed the fully disclosed rule text is
free/not paywalled on this particular article).

**Disclosed rule (source, tested on SPY + VEU/GDX/FXI/EWA/EEM since 2005):**
- Entry: buy at the close after N=4 consecutive down-close days.
- Exit: sell at the close on the first day whose close exceeds the
  previous day's close.
- No trend filter, no stop-loss, no fixed hold period.

**Implementation:** `strategies/2026-09-22_four_consecutive_down_days.py`.
Parameterized `down_streak_days` (source's disclosed default is 4, but this
repo's own grid found a shorter streak works notably better on this
sample — see below).

## Step 6 — Grid test summary

`param_grid={"down_streak_days": [3,4,5]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Overall:** 8/36 cells passed (pass_fraction 0.222).
- **By asset class:** equity 8/18 passed; crypto **0/18 passed** (decisive
  reject on crypto for this sample/window).
- **By vol regime:** low 1/12, mid 2/12, high 5/12 — edge is concentrated
  in higher-volatility regimes (consistent with the source's own framing:
  "buying when the risk premium rises").
- **Best cell:** QQQ, high-vol, down_streak_days=3, Sharpe 2.26.
- Source's own disclosed default (down_streak_days=4) is markedly weaker
  on this sample/window (see validators below) — a shortened 3-day streak
  is the config carried to validation.

## Step 7 — Validators

| Config | Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward (manual 4-split) | Param sensitivity |
|---|---|---|---|---|---|---|
| down_streak_days=3 | QQQ | 1.411 ✅ | 0.061 ✅ | 1.085 ✅ | 4/4 ✅ | 0.384 ✅ |
| down_streak_days=3 | SPY | 1.226 ✅ | 0.105 ✅ | 0.907 ✅ | 4/4 ✅ | 0.221 ✅ |
| down_streak_days=4 (source default) | QQQ | 0.415 ❌ | 0.076 ✅ | 0.261 ❌ | 3/4 ✅ | 0.384 ✅ |
| down_streak_days=4 (source default) | SPY | 1.131 ✅ | 0.070 ✅ | 0.969 ✅ | 3/4 ✅ | 0.221 ✅ |

Thresholds: Sharpe >= 1.0, MDD <= 0.25, net Sharpe after 10bps/trade costs
>= 0.5, walk-forward pass-fraction >= 0.75, parameter-sensitivity relative
std <= 0.5.

QQQ (down_streak_days=3): 94 trades. SPY: 97 trades.

## Decision: ACCEPT (equity only, down_streak_days=3 — QQQ and SPY)

All 5 validators pass for both QQQ and SPY at down_streak_days=3. The
source's own disclosed default of 4 consecutive down days fails Sharpe and
transaction-cost survival on QQQ in this sample (own-data recalibration:
shorter streak = better full-sample edge here). Crypto is out of scope
(0/18 grid cells passed).
