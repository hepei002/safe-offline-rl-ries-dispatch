from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.optimization.deterministic_dispatch import (
    CONFIG_PATH,
    load_dispatch_inputs,
    solve_dispatch_day,
)
from src.policies.evaluation import (
    dataframe_to_markdown_table,
    ensure_evaluation_columns,
    summarize_many,
)
from src.policies.random_policy import run_safe_random_policy
from src.policies.rolling_mpc import run_rolling_mpc
from src.policies.rule_based import run_rule_based_policy


POLICY_CONFIG_PATH = ROOT / "configs" / "behavior_policies.yaml"
OUTPUT_DIR = ROOT / "results" / "week5_behavior_policies"
TRAJECTORY_DIR = OUTPUT_DIR / "trajectories"


def load_policy_config() -> dict:
    return yaml.safe_load(POLICY_CONFIG_PATH.read_text(encoding="utf-8"))


def select_evaluation_frame(frame: pd.DataFrame, policy_config: dict) -> pd.DataFrame:
    evaluation = policy_config["evaluation"]
    start = pd.Timestamp(evaluation["start_utc"])
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    else:
        start = start.tz_convert("UTC")
    hours = int(evaluation["hours"])
    lookahead = int(evaluation["lookahead_hours"])
    return frame.loc[start : start + pd.Timedelta(hours=hours + lookahead - 2)].copy()


def run_perfect_information(
    frame: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
    *,
    evaluation_hours: int,
) -> pd.DataFrame:
    result = solve_dispatch_day(
        frame.iloc[:evaluation_hours],
        system_config,
        policy_config,
        enforce_terminal_soc=False,
    )
    dispatch = result.frame
    dispatch["mpc_solve_time_s"] = 0.0
    return ensure_evaluation_columns(dispatch, system_config, policy_config)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TRAJECTORY_DIR.mkdir(parents=True, exist_ok=True)

    frame, system_config = load_dispatch_inputs(system_config_path=CONFIG_PATH)
    policy_config = load_policy_config()
    evaluation_hours = int(policy_config["evaluation"]["hours"])
    evaluation_frame = select_evaluation_frame(frame, policy_config)
    actual_frame = evaluation_frame.iloc[:evaluation_hours].copy()

    dispatches = {
        "perfect_information_lp": run_perfect_information(
            evaluation_frame,
            system_config,
            policy_config,
            evaluation_hours=evaluation_hours,
        ),
        "rolling_mpc": run_rolling_mpc(
            evaluation_frame,
            system_config,
            policy_config,
            evaluation_hours=evaluation_hours,
            noisy=False,
        ),
        "noisy_rolling_mpc": run_rolling_mpc(
            evaluation_frame,
            system_config,
            policy_config,
            evaluation_hours=evaluation_hours,
            noisy=True,
            seed=int(policy_config.get("noisy_mpc", {}).get("seed", 42)),
        ),
        "rule_based": run_rule_based_policy(
            actual_frame,
            system_config,
            policy_config,
        ),
        "safe_random": run_safe_random_policy(
            actual_frame,
            system_config,
            policy_config,
            seed=int(policy_config.get("safe_random", {}).get("seed", 2026)),
        ),
    }

    for name, dispatch in dispatches.items():
        dispatch.to_csv(TRAJECTORY_DIR / f"{name}.csv", index_label="utc_timestamp")

    summary = summarize_many(dispatches, system_config, policy_config)
    summary.to_csv(OUTPUT_DIR / "behavior_policy_benchmark.csv", index=False)
    (OUTPUT_DIR / "behavior_policy_benchmark.md").write_text(
        dataframe_to_markdown_table(summary),
        encoding="utf-8",
    )
    print(summary.to_string(index=False))
    print(f"output_dir={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
