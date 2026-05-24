from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import mlflow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--out", type=str, default="artifacts")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", str(out / "mlruns")))
    with mlflow.start_run(run_name="baseline"):
        # Replace with real training; this baseline just logs counts.
        rows = sum(1 for _ in open(args.data))
        mlflow.log_param("rows", rows)
        mlflow.log_metric("placeholder_score", 0.5)
        (out / "model.json").write_text(json.dumps({"version": "0.1"}))
        mlflow.log_artifact(str(out / "model.json"))


if __name__ == "__main__":
    main()
