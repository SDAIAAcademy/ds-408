# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Review rules for metric files, as code. Runs in continuous integration on every pull request.

    uv run ci/check_metrics.py --repo <metrics repository> --base main --head HEAD

The repository holds metrics/*.yml, CHANGELOG.md and approvals.yml. The check compares the metric
files at --head with those at --base and prints one line per finding; it exits 1 when any rule fails.

Rules
  R1  every metric has owner, version (x.y.z), status and description
  R2  a certified metric has at least one test
  R3  a changed metric has a higher version: major when its meaning changed (type, dataset, agg,
      expr, filter, numerator, denominator, base, inputs) and it was certified; minor for a new
      field or a status change; patch for words only (description, label, synonyms)
  R4  CHANGELOG.md names each changed metric with its new version
  R5  approvals.yml has an approval of each changed metric's new version by its owner, who is not
      the author of the last commit
  R6  a metric is removed only after it was deprecated
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

MEANING = ("type", "dataset", "agg", "expr", "filter", "numerator", "denominator", "base", "inputs")
WORDS = ("description", "label", "ai", "unit")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(repo, *args) -> str:
    return subprocess.run(["git", "-c", "core.longpaths=true", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", check=True).stdout


def metrics_at(repo, rev) -> dict[str, dict]:
    out = {}
    names = [n for n in git(repo, "ls-tree", "--name-only", rev, "metrics/").split() if n.endswith(".yml")]
    for n in names:
        doc = yaml.safe_load(git(repo, "show", f"{rev}:{n}")) or []
        for m in doc if isinstance(doc, list) else [doc]:
            out[m["name"]] = m
    return out


def version(v) -> tuple[int, int, int] | None:
    m = SEMVER.match(str(v or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def needed_bump(old: dict, new: dict) -> str | None:
    if any(old.get(k) != new.get(k) for k in MEANING):
        return "major" if old.get("status") == "certified" else "minor"
    if old.get("status") != new.get("status") or set(new) - set(old):
        return "minor"
    if any(old.get(k) != new.get(k) for k in WORDS) or old != new:
        return "patch"
    return None


def bumped(old_v, new_v, kind) -> bool:
    o, n = version(old_v), version(new_v)
    if not o or not n or n <= o:
        return False
    if kind == "major":
        return n[0] > o[0]
    if kind == "minor":
        return n[0] > o[0] or n[1] > o[1]
    return True


def check(repo, base, head) -> list[str]:
    old, new = metrics_at(repo, base), metrics_at(repo, head)
    findings = []
    for name, m in new.items():
        for k in ("owner", "version", "status", "description"):
            if not m.get(k):
                findings.append(f"R1 {name}: missing {k}")
        if m.get("version") and not version(m["version"]):
            findings.append(f"R1 {name}: version {m['version']!r} is not x.y.z")
        if m.get("status") == "certified" and not m.get("tests") and m.get("type", "simple") == "simple":
            findings.append(f"R2 {name}: certified without a test")
    changed = {}
    for name, m in new.items():
        if name not in old:
            changed[name] = m
            continue
        kind = needed_bump(old[name], m)
        if kind:
            changed[name] = m
            if not bumped(old[name].get("version"), m.get("version"), kind):
                findings.append(f"R3 {name}: a {kind} change needs a {kind} version bump "
                                f"(was {old[name].get('version')}, now {m.get('version')})")
    for name, m in old.items():
        if name not in new and m.get("status") != "deprecated":
            findings.append(f"R6 {name}: removed without being deprecated first")
    log_path = Path(repo) / "CHANGELOG.md"
    log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    appr_path = Path(repo) / "approvals.yml"
    approvals = (yaml.safe_load(appr_path.read_text(encoding="utf-8")) or []) if appr_path.exists() else []
    author = git(repo, "log", "-1", "--format=%an", head).strip()
    for name, m in changed.items():
        if not re.search(rf"\b{re.escape(name)}\b.*\b{re.escape(str(m.get('version')))}\b", log):
            findings.append(f"R4 {name}: CHANGELOG.md has no line for {name} {m.get('version')}")
        ok = [a for a in approvals if a.get("metric") == name and str(a.get("version")) == str(m.get("version"))]
        if not ok:
            findings.append(f"R5 {name}: no approval of version {m.get('version')}")
        elif not any(a.get("approved_by") == m.get("owner") and a.get("approved_by") != author for a in ok):
            findings.append(f"R5 {name}: approved by {ok[0].get('approved_by')!r}; needs the owner "
                            f"{m.get('owner')!r}, who is not the author {author!r}")
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", default="main")
    ap.add_argument("--head", default="HEAD")
    a = ap.parse_args(argv)
    findings = check(a.repo, a.base, a.head)
    for f in findings:
        print("FAIL", f)
    print("metrics check:", "passed" if not findings else f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
