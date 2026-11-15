# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 1.3 · A metric change taken through review
#
# Day 1 · Session 3 (Ownership and change control) · 25 min. Finance asks for the billed amount without VAT.
# You write Qamar Telecom's change process, make the change on a branch of a metrics repository, let the review
# rules in continuous integration stop it, and fix it until the owner's approval lets it merge.
#
# **AI-tutor.** An assistant may explain a git message; the process and the change are yours.
#
# **Reference state.** `data/metrics/` (the certified metric files) and `ci/check_metrics.py` (the review rules
# R1 to R6, as code). The lab builds a fresh local git repository in `artifacts/D1_3/metrics-repo`; nothing is
# pushed anywhere.
#
# **Tasks**
# - [ ] 1 · Read the review rules (4')
# - [ ] 2 · Write the change process (6')
# - [ ] 3 · Make the change on a branch (5')
# - [ ] 4 · Run the check and read why it fails (4')
# - [ ] 5 · Fix, pass and merge (6')
# - [ ] ✱ Stretch · A words-only change: which bump does it need?

# %%
import os, sys, subprocess
from pathlib import Path

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    REPO_URL = "https://github.com/SDAIAAcademy/ds-408.git"
    if not Path("/content/ds-408").exists():
        subprocess.run(["git", "clone", "-q", REPO_URL, "/content/ds-408"], check=True)
    os.chdir("/content/ds-408/labs")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements-colab.txt"], check=True)
else:
    while not Path("qamar.py").exists() and Path.cwd() != Path.cwd().parent:
        os.chdir("..")  # solutions/ notebooks run from labs/
sys.path.insert(0, os.getcwd())

import shutil
import yaml
import qamar as Q

REPO = Q.lab_dir("D1_3") / "metrics-repo"
LABS = Path.cwd()
STEWARD = ("Zeyad Al-Juraisy", "zeyad@qamar.example")
OWNER = ("Jood Al-Muhaisen", "jood@qamar.example")


def git(*args, who=STEWARD, check=True):
    env = dict(os.environ, GIT_AUTHOR_NAME=who[0], GIT_AUTHOR_EMAIL=who[1], GIT_COMMITTER_NAME=who[0],
               GIT_COMMITTER_EMAIL=who[1], GIT_AUTHOR_DATE="2026-07-01T09:00:00+03:00",
               GIT_COMMITTER_DATE="2026-07-01T09:00:00+03:00")
    r = subprocess.run(["git", "-c", "core.longpaths=true", "-c", "core.autocrlf=false", "-C", str(REPO), *args], capture_output=True, text=True, encoding="utf-8", env=env)
    if check and r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()


def ci() -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(LABS / "ci" / "check_metrics.py"), "--repo", str(REPO), "--base", "main",
                        "--head", "HEAD"], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout.strip()


# The starting repository: the certified metric files on main
(REPO / "metrics").mkdir(parents=True)
for f in sorted((LABS / "data" / "metrics").glob("*.yml")):
    shutil.copy(f, REPO / "metrics" / f.name)
(REPO / "CHANGELOG.md").write_text("# Metric changes\n\n- 2026-06-01 all metrics 1.0.0: first certified catalogue\n", encoding="utf-8")
(REPO / "approvals.yml").write_text("[]\n", encoding="utf-8")
git("init", "-q", "-b", "main")
git("add", "-A")
git("commit", "-q", "-m", "Certified metric catalogue 1.0.0")
print(git("log", "--oneline"))

# %% [markdown]
# ## 1 · Read the review rules (4')
#
# The rules are code, so a reviewer's memory is not the control. Read the docstring below, then answer for
# yourself: which rules would a pull request that only fixes a typo in a description have to satisfy?

# %%
print(subprocess.run([sys.executable, str(LABS / "ci" / "check_metrics.py"), "--help"], capture_output=True, text=True,
                     encoding="utf-8").stdout)
print((LABS / "ci" / "check_metrics.py").read_text(encoding="utf-8").split('"""')[1])

# %% [markdown]
# ## 2 · Write the change process (6')
#
# The rules say *what* must be true before a merge; the process says *who* does what. Fill every key: who may
# request a change, who approves it, how each kind of change is versioned, how long a breaking change is announced
# before it takes effect, and what happens to reports that use the old version.
#
# ✏️ **Exercise** · Fill `PROCESS`, then write it as `CHANGE_PROCESS.md` in the repository.

# %%
def change_process() -> dict:
    # BEGIN SOLUTION
    return {
        "request": "Anyone may open a change request; it names the metric, the reason and the reports affected",
        "implement": "The data platform team (steward) edits the metric file on a branch and opens a pull request",
        "approve": "The metric's owner approves the new version in approvals.yml; the author cannot approve",
        "versioning": "Meaning changed: major. New field or status: minor. Words only: patch",
        "notice": "A major change is announced two monthly closes before it takes effect",
        "old_version": "The old meaning stays available under a new name, marked deprecated, until its reports move",
        "checks": "CI runs the review rules R1 to R6 and the reconciliation tests; both must pass to merge",
    }
    # END SOLUTION


# %%
try:
    PROCESS = change_process()
except NotImplementedError:
    PROCESS = Q.reference("d1_3_process")
md = "# Metric change process\n\n" + "\n".join(f"- **{k.replace('_', ' ').title()}.** {v}" for k, v in PROCESS.items()) + "\n"
(REPO / "CHANGE_PROCESS.md").write_text(md, encoding="utf-8")
print(md)
Q.check({"request", "approve", "versioning", "notice"} <= set(PROCESS), "the process says who requests, who approves, versions and notice")
git("add", "CHANGE_PROCESS.md")
git("commit", "-q", "-m", "Add the change process")

# %% [markdown]
# ## 3 · Make the change on a branch (5')
#
# Change request CR-07 from Jood Al-Muhaisen: "the board pack reports revenue without VAT; make `billed_amount`
# exclude VAT (15%)". The steward makes the edit the quick way: the expression only.
#
# ✏️ **Exercise** · On a branch `cr-07`, change the expression of `billed_amount` in `metrics/billing.yml` to the
# amount without VAT, and commit it as the steward. Change nothing else yet.

# %%
def edit_metric(path: Path, name: str, **changes):
    docs = yaml.safe_load(path.read_text(encoding="utf-8"))
    for m in docs:
        if m["name"] == name:
            m.update(changes)
    path.write_text(yaml.safe_dump(docs, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")


def make_change():
    # BEGIN SOLUTION
    edit_metric(REPO / "metrics" / "billing.yml", "billed_amount", expr="amount_due / 1.15")
    git("commit", "-q", "-am", "CR-07: billed amount without VAT")
    # END SOLUTION


def supplied_change():  # the safety net applies this when the exercise is skipped
    edit_metric(REPO / "metrics" / "billing.yml", "billed_amount", expr="amount_due / 1.15")
    git("commit", "-q", "-am", "CR-07: billed amount without VAT (supplied)")


# %%
git("checkout", "-q", "-b", "cr-07")
try:
    make_change()
except NotImplementedError:
    supplied_change()
print(git("log", "--oneline", "main..HEAD"))
Q.check("1.15" in git("show", "HEAD:metrics/billing.yml"), "the branch changes the expression of billed_amount")

# %% [markdown]
# ## 4 · Run the check and read why it fails (4')

# %%
code, out = ci()
print(out)
rules = sorted({line.split()[1] for line in out.splitlines() if line.startswith("FAIL")})
print("rules that failed:", rules)
Q.check(code == 1 and {"R3", "R4", "R5"} <= set(rules), "CI stops the change: version, changelog, approval")

# %% [markdown]
# 🔍 R3 asks for a **major** bump. Why does a different number for the same name break the reports that use it,
# even though nobody changed those reports?
#
# ## 5 · Fix, pass and merge (6')
#
# ✏️ **Exercise** · Bump the version as R3 asks, add the CHANGELOG line, and have the owner (not the steward)
# add her approval. Commit, run the check until it passes, then merge into `main`.

# %%
def fix_change():
    # BEGIN SOLUTION
    edit_metric(REPO / "metrics" / "billing.yml", "billed_amount", version="2.0.0",
                description="Total amount on bills for the service month, without VAT (CR-07), before disputes")
    with open(REPO / "CHANGELOG.md", "a", encoding="utf-8") as f:
        f.write("- 2026-07-01 billed_amount 2.0.0: without VAT (CR-07). Breaking: board pack and ARPA move together\n")
    git("commit", "-q", "-am", "CR-07: major version and changelog")
    (REPO / "approvals.yml").write_text(yaml.safe_dump([{"metric": "billed_amount", "version": "2.0.0",
                                                         "approved_by": OWNER[0], "request": "CR-07"}], sort_keys=False),
                                        encoding="utf-8")
    git("commit", "-q", "-am", "CR-07: owner approval", who=STEWARD)
    # END SOLUTION


def supplied_fix():  # the safety net
    edit_metric(REPO / "metrics" / "billing.yml", "billed_amount", version="2.0.0")
    with open(REPO / "CHANGELOG.md", "a", encoding="utf-8") as f:
        f.write("- 2026-07-01 billed_amount 2.0.0: without VAT (CR-07)\n")
    (REPO / "approvals.yml").write_text(yaml.safe_dump([{"metric": "billed_amount", "version": "2.0.0", "approved_by": OWNER[0]}]),
                                        encoding="utf-8")
    git("commit", "-q", "-am", "CR-07: version, changelog, approval (supplied)")


try:
    fix_change()
except NotImplementedError:
    supplied_fix()
code, out = ci()
print(out)
if code == 0:
    git("checkout", "-q", "main")
    git("merge", "-q", "--no-ff", "cr-07", "-m", "Merge CR-07")
print(git("log", "--oneline", "--graph", "-8"))
Q.check(code == 0, "the review rules pass")
Q.check("2.0.0" in (REPO / "metrics" / "billing.yml").read_text(encoding="utf-8") and git("branch", "--show-current") == "main",
        "billed_amount 2.0.0 is on main")

# %% [markdown]
# 🔍 The last commit was made by the steward, yet R5 passed: R5 checks who is named as approver, not who typed
# it. In GitHub, what replaces this file so the approval cannot be typed by the author?
#
# ## ✱ Stretch · A words-only change
#
# On a new branch, add an Arabic synonym to `billed_amount` without changing the version. Which rule fails, and
# which bump does it ask for?

# %%
def stretch():
    # BEGIN SOLUTION
    git("checkout", "-q", "-b", "cr-08")
    docs = yaml.safe_load((REPO / "metrics" / "billing.yml").read_text(encoding="utf-8"))
    docs[0]["ai"]["synonyms"]["ar"].append("الإيراد المفوتر")
    (REPO / "metrics" / "billing.yml").write_text(yaml.safe_dump(docs, allow_unicode=True, sort_keys=False), encoding="utf-8")
    git("commit", "-q", "-am", "CR-08: Arabic synonym")
    print(ci()[1])
    git("checkout", "-q", "main")
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why must the approver not be the author of the change?
#
# <details><summary>Answer</summary>Four eyes: the owner answers for the meaning, the author for the edit. One
# person doing both is no review.</details>
#
# 2. CR-07 changed what `billed_amount` means. What else could the steward have done instead of a major version?
#
# <details><summary>Answer</summary>Add a new metric `billed_amount_ex_vat` (minor change, nothing breaks) and
# deprecate the old one once its reports moved.</details>
#
# 3. The check passed. What does it still not prove?
#
# <details><summary>Answer</summary>That the new definition is right: only the reconciliation tests and the owner's
# reading say that. Rules check the process, tests check the numbers.</details>
#
# **Carry forward.** `artifacts/D1_3/metrics-repo` with `CHANGE_PROCESS.md` and the merged change: the pattern
# of your capstone repository (copy `ci/metrics-ci.yml` there).
