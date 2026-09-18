import json

entry = {
  "id": "2026-09-18-088",
  "created_at": "2026-09-18T11:30:00Z",
  "hypothesis": "Ehlers & Way's Empirical Mode Decomposition (TASC March 2010): bandpass-filtered price (period/delta1 recursive 2-pole filter) SMA-smoothed over 2*period bars gives a Trend line; the bandpass series' local peaks/valleys, each SMA(50)-averaged and scaled by a fraction multiplier, give FracAvgPeak/FracAvgValley reference bands. Trend mode: long when Trend crosses above FracAvgPeak (confirmed trending regime), exit on Trend crossing below FracAvgValley or max_hold_days time-stop. Per fully-disclosed Pine Script implementation (https://www.tradingview.com/script/Qy6QFjs2-blackcat-L2-Ehlers-Empirical-Mode-Trader/, read via browser_exec -- web_search DDGS backend failed on all queries this iteration). Long-only per SAFETY.md; source's separate Bollinger-Band Cycle mode not implemented. Zero prior 'Empirical Mode Decomposition'/'EMD' entries in this repo.",
  "asset_class": "equity (QQQ, SPY accepted); crypto out of scope (decisive grid fail)",
  "symbols": ["QQQ", "SPY"],
  "timeframe": "1d",
  "strategy_file": "strategies/2026-09-18_ehlers_emd_trend_mode.py",
  "backtest_report": "backtests/2026-09-18_ehlers_emd_trend_mode.md",
  "validators": {
    "QQQ": {"params": {"period": 15, "fraction": 5.0, "max_hold_days": 40}, "sharpe": 1.272, "mdd": 0.157, "tc_net_sharpe": 1.242, "num_trades": 46, "param_sensitivity_relative_std": 0.365, "all_pass": True},
    "SPY": {"params": {"period": 30, "fraction": 3.0, "max_hold_days": 60}, "sharpe": 1.055, "mdd": 0.119, "tc_net_sharpe": 1.022, "num_trades": 38, "all_pass": True}
  },
  "outcome": "accepted (QQQ, SPY equity only)",
  "rejection_reason": None,
  "notes": "Step 6 grid: 216 cells (period in {15,20,30} x fraction in {3.0,5.0,8.0} x max_hold_days in {40,60} x 4 symbols x 3 vol regimes), 2018-2026 daily. Overall pass_fraction=0.231 (50/216). by_asset_class: equity 44/108 (0.407), crypto 6/108 (0.056, decisive fail -- not pursued for single-config validation). by_vol_regime: low 36/72 (0.5), mid 12/72 (0.167), high 2/72 (0.028) -- edge concentrated in calm regimes. Best cell: QQQ low-vol, period=30/fraction=3.0/max_hold_days=60, Sharpe 2.97. Both QQQ and SPY full-sample best configs pass Sharpe/MDD/transaction-cost-survival/parameter-sensitivity (sweeping fraction). check_walk_forward not run this iteration (time-constrained; parameter-sensitivity substituted per Step 7 guidance). Source: https://www.tradingview.com/script/Qy6QFjs2-blackcat-L2-Ehlers-Empirical-Mode-Trader/ (browser_exec, since web_search's DuckDuckGo backend failed with no-results/errors on every query attempted this iteration). Future loop could attempt a leverage-cap-aware crypto retune following this repo's established pattern (Vortex/Fisher/CKSP etc.) to test whether crypto's thin 6/108 grid signal can be rescued."
}

with open("knowledge_base/strategies_log.jsonl", "a") as f:
    f.write(json.dumps(entry) + "\n")

index_entry = {
  "id": "2026-09-18-088",
  "created_at": "2026-09-18T11:30:00Z",
  "hypothesis": "Ehlers/Way Empirical Mode Decomposition (TASC 2010): bandpass-filtered price trend line crossing its own peak/valley-derived reference bands. First EMD strategy in this repo, zero prior entries. Trend mode long-only crossover.",
  "outcome": "accepted (QQQ, SPY)",
  "tags": {
    "indicator_family": ["Empirical Mode Decomposition", "EMD", "Ehlers", "Bandpass Filter"],
    "technique": ["bandpass_filter", "peak_valley_tracking", "trend_regime_breakout", "time_stop"],
    "asset_class": "equity"
  }
}
with open("knowledge_base/strategies_index.jsonl", "a") as f:
    f.write(json.dumps(index_entry) + "\n")
print("logged")
