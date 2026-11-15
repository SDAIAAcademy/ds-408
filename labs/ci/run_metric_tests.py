# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
"""Run every metric's reconciliation tests and exit 1 when one fails.

    uv run ci/run_metric_tests.py [--model semantic/model.yaml] [--metrics metrics]

Run from the root of a repository laid out like labs/: qsem.py and qamar.py beside the data, or
from labs/ itself (the defaults).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
import qamar as Q  # noqa: E402
import qsem as S  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="data/semantic/qamar_model.yaml")
    ap.add_argument("--metrics", default="data/metrics")
    a = ap.parse_args(argv)
    model = S.Model.load(a.model, Q.db(), metrics_dir=a.metrics)
    res = S.run_tests(model)
    print(res[["metric", "expected", "actual", "passed"]].to_string(index=False))
    print("reconciliation tests:", "passed" if res.passed.all() else f"{(~res.passed).sum()} failed")
    return 0 if res.passed.all() else 1


if __name__ == "__main__":
    sys.exit(main())
