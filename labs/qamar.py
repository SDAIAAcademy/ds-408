"""Shared helpers for the DS-408 labs (Qamar Telecom).

    import qamar as Q
    con = Q.db()                 # DuckDB with one view per mart
    Q.check(cond, "message")     # prints a tick or a cross, and stops the solution run on a cross
    Q.reference("d1_1_rates")    # the reference result a safety net falls back on
    Q.pick(full, quick)          # the small value when QAMAR_QUICK=1
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

import duckdb
import pandas as pd
import yaml

LABS = Path(__file__).resolve().parent
DATA = LABS / "data"
MARTS = DATA / "marts"
REF = DATA / "reference"
ARTIFACTS = LABS / "artifacts"
QUICK = os.environ.get("QAMAR_QUICK", "0") == "1"
DATA_END = "2026-06-30"  # the data cut-off: the labs' "today" is the day after

try:  # Windows consoles default to a legacy code page; the labs print Arabic and ticks
    import sys as _sys
    _sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)


def pick(full, quick):
    """The full value, or the small one in quick mode."""
    return quick if QUICK else full


def check(cond, message: str) -> None:
    """Print a tick or a cross. A cross stops a solution run: the solutions must pass every check."""
    print(("✅ " if cond else "❌ ") + message)
    if not cond:
        raise AssertionError(message)


def reference(name: str):
    """The reference result of an exercise, for the safety net after it."""
    return json.loads((REF / f"{name}.json").read_text(encoding="utf-8"))


def yaml_load(path) -> dict:
    return yaml.safe_load(Path(LABS / path).read_text(encoding="utf-8"))


def yaml_dump(obj, path=None) -> str:
    text = yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=110)
    if path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return text


def lab_dir(name: str, reset: bool = True) -> Path:
    """A fresh working folder under labs/artifacts/ for one lab."""
    d = ARTIFACTS / name
    if reset and d.exists():
        def writable(func, path, _):  # git marks its object files read-only on Windows
            os.chmod(path, 0o700)
            func(path)
        shutil.rmtree(d, onerror=writable)
    d.mkdir(parents=True, exist_ok=True)
    return d


def db(events: bool = False) -> duckdb.DuckDBPyConnection:
    """An in-memory DuckDB with one view per mart file. events=True also builds fct_usage_event."""
    con = duckdb.connect()
    for f in sorted(MARTS.glob("*.parquet")):
        con.execute(f"CREATE VIEW {f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')")
    if events:
        usage_events(con)
    return con


def usage_events(con, rows: int | None = None) -> int:
    """Build fct_usage_event: one row per data or voice session, deterministic arithmetic, no file.

    Every monthly usage row of fct_usage_monthly is spread over sessions so that the events add up to
    the monthly totals. Full size is about 2.1 million rows; quick mode keeps one line in eight.
    """
    keep = pick(1, 8)
    con.execute(f"""
        CREATE OR REPLACE TABLE fct_usage_event AS
        WITH m AS (
          SELECT u.*, row_number() OVER (ORDER BY line_id, usage_month) AS k
          FROM fct_usage_monthly u
          WHERE CAST(substr(line_id, 2) AS INTEGER) % {keep} = 0
        ), s AS (
          SELECT m.*, i, 40 + (k * 7) % 40 AS n
          FROM m, range(0, 80) r(i)
        )
        SELECT line_id,
               usage_month + CAST((i * 13 + k) % 28 AS INTEGER) AS event_date,
               CASE WHEN i % 3 = 0 AND voice_min > 0 THEN 'voice' ELSE 'data' END AS kind,
               CASE WHEN i % 3 = 0 AND voice_min > 0 THEN 0 ELSE round(data_gb * 1024 / (n - n // 3), 3) END AS mb,
               CASE WHEN i % 3 = 0 AND voice_min > 0 THEN round(voice_min * 60.0 / (n // 3 + 1), 1) ELSE 0 END AS seconds
        FROM s WHERE i < n
    """)
    return con.execute("SELECT count(*) FROM fct_usage_event").fetchone()[0]


def timed(fn, repeat: int | None = None) -> float:
    """Median wall time of fn() in milliseconds over a few runs (after one warm-up run)."""
    repeat = repeat or pick(7, 3)
    fn()
    times = []
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t) * 1000)
    times.sort()
    return round(times[len(times) // 2], 2)


def show(df: pd.DataFrame, n: int = 12) -> None:
    print(df.head(n).to_string(index=False))
