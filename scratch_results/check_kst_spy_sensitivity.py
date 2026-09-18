import importlib.util
import sys
from datetime import datetime

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

from loaders import load_equity  # noqa: E402
from validators import check_sharpe_ratio, check_parameter_sensitivity  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-14_kst_sizing_sma_trend.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

start = datetime(2015, 1, 1)
end = datetime(2026, 9, 1)
price_df = load_equity("SPY", start, end)

base = dict(trend_window=40, zscore_window=60, sensitivity=0.4, deadband=0.3)

param_grid_results = {}
for s in [0.2, 0.3, 0.4, 0.5, 0.6]:
    p2 = dict(base)
    p2["sensitivity"] = s
    r2 = strat.generate_returns(price_df, **p2)
    sh_pass2, sh_ev2 = check_sharpe_ratio(r2)
    param_grid_results[f"sensitivity={s}"] = sh_ev2.get("value")

ps_pass, ps_ev = check_parameter_sensitivity(param_grid_results)
print(ps_pass, ps_ev)
