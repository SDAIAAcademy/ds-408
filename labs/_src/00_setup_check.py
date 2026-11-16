# %% [markdown]
# # Setup check
#
# Run this once before Day 1, on your laptop or in Colab. It imports every dependency, reads the case-study data,
# runs one query through the semantic layer, replays one recorded reply of the stand-in model, and, only if you
# set a free OpenRouter key, asks the hosted model one question. It prints what is missing.

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
        os.chdir("..")
sys.path.insert(0, os.getcwd())

# %%
import importlib

missing = []
print("Python", sys.version.split()[0])
for name in ["duckdb", "pandas", "yaml", "hijridate"]:
    try:
        mod = importlib.import_module(name)
        print(f"  {name:10s} {getattr(mod, '__version__', 'ok')}")
    except ImportError:
        missing.append(name)
        print(f"  {name:10s} MISSING")
print("missing:", missing or "nothing")

# %%
import qamar as Q
import qsem as S
import muhsi as D

con = Q.db()
rows = con.execute("SELECT COUNT(*) FROM fct_bill").fetchone()[0]
print(f"case data: {rows:,} bills")
model = S.Model.load("data/semantic/qamar_model.yaml", con, metrics_dir="data/metrics")
print("collection rate, March 2026:", round(model.value("collection_rate", ["time.month = DATE '2026-03-01'"]), 4))
qs = D.load_set("data/assistant/certified_60.yaml")
print("stand-in reply to", qs[0]["id"], "->", D.ask(qs[0], "full", 1))

# %%
if os.environ.get("OPENROUTER_API_KEY") and D.MODE == "live":
    try:
        print("live model", D.LIVE_MODEL, "->", D.ask(qs[0], "full", 1, metrics=list(model.metrics.values())))
    except Exception as e:  # noqa: BLE001 - the setup check reports, it does not stop
        print("live model did not answer:", e)
else:
    print("live model: off (optional; set QAMAR_MODEL_MODE=live and OPENROUTER_API_KEY for the stretch of Lab 3.2)")
print("✅ ready" if not missing else "❌ install the missing packages: uv sync (locally) or rerun the first cell (Colab)")
