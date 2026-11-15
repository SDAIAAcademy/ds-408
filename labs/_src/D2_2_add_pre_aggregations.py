# %% [markdown]
# # Lab 2.2 · Add pre-aggregations for the ten most-asked metrics and measure query latency before and after
#
# Day 2 · Session 2 (Performance and cost) · 25 min.
#
# REPLACE: what participants build in this lab, in two or three lines.
#
# **Tasks**
# - [ ] REPLACE: the tasks, each with its minutes; they add up to 25
# - [ ] ✱ Stretch · REPLACE: an extension for those who finish early

# %%
import os, sys, subprocess
from pathlib import Path

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    REPO_URL = "https://github.com/SDAIAAcademy/ds-408.git"
    if not Path("/content/ds-408").exists():
        subprocess.run(["git", "clone", "-q", REPO_URL, "/content/ds-408"], check=True)
    os.chdir("/content/ds-408/labs")
else:
    while not Path("_tools").exists() and Path.cwd() != Path.cwd().parent:
        os.chdir("..")  # solutions/ notebooks run from labs/
sys.path.insert(0, os.getcwd())

# %% [markdown]
# ## 1 · REPLACE: the first task
#
# REPLACE: what to do and why, in two sentences.

# %%
# ✏️ Exercise
def first_task():
    # BEGIN SOLUTION
    return "the reference result"
    # END SOLUTION

# %%
# Check, with a safety net: the cells below still run when the exercise is not done yet
try:
    result = first_task()
except NotImplementedError:
    result = "the reference result"
print(result)
