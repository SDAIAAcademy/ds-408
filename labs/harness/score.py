# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
"""Score Muhsi on a certified question set, so a reviewer can re-run any figure in a report.

    uv run python harness/score.py                                   # full context, run 1
    uv run python harness/score.py --variant no_synonyms --runs 1 2 3
    uv run python harness/score.py --set artifacts/D3_1/certified_60.yaml --out artifacts/score

Run from labs/. Prints the summary and writes results.csv and summary.json with the hashes of every
input (question set, recorded replies, model, metrics), so two runs can be shown to be the same run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LABS))
import muhsi as D  # noqa: E402
import qamar as Q  # noqa: E402
import qsem as S  # noqa: E402

SCORER_VERSION = "1.0.0"


def digest(paths) -> str:
    h = hashlib.sha256()
    for p in sorted(Path(x) for x in paths):
        h.update(p.name.encode())
        h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def inputs(set_path: Path) -> dict:
    return {"set": digest([set_path]), "replies": digest([LABS / "data/assistant/replies.jsonl"]) if D.MODE != "live" else "live",
            "model": digest([LABS / "data/semantic/qamar_model.yaml"]), "metrics": digest((LABS / "data/metrics").glob("*.yml")),
            "scorer": SCORER_VERSION, "mode": D.MODE if D.MODE != "live" else f"live:{D.LIVE_MODEL}",
            "tolerance": D.TOLERANCE, "plausible": list(D.PLAUSIBLE)}


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--set", default="data/assistant/certified_60.yaml")
    ap.add_argument("--variant", default="full", choices=D.VARIANTS)
    ap.add_argument("--runs", type=int, nargs="+", default=[1])
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    set_path = LABS / a.set
    model = S.Model.load(LABS / "data/semantic/qamar_model.yaml", Q.db(), metrics_dir=LABS / "data/metrics")
    qs = D.load_set(set_path)
    table = D.score(model, qs, a.variant, runs=tuple(a.runs), metrics=list(model.metrics.values()))
    summ = D.summary(table)
    report = {"inputs": inputs(set_path), "variant": a.variant, "runs": a.runs, "n": int(len(table)),
              "accuracy": float(summ.accuracy.iloc[0]), "wrong_plausible": float(summ.wrong_plausible.iloc[0]),
              "outcomes": {k: int(v) for k, v in table.outcome.value_counts().sort_index().items()}}
    print(json.dumps(report, indent=1, ensure_ascii=False))
    if a.out:
        out = LABS / a.out
        out.mkdir(parents=True, exist_ok=True)
        table.to_csv(out / "results.csv", index=False, lineterminator="\n")
        (out / "summary.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    main()
