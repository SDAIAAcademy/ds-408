"""qossie: export the course's semantic model to an Apache Ossie document and run it on a second engine.

Apache Ossie (formerly Open Semantic Interchange) core specification, draft 0.3.0.dev0: one model per
document with `version`, `name`, `datasets` (source, primary_key, fields with `expression.sql` and
optional `dialects`), `relationships` (from the many side to the one side) and model-scoped `metrics`.
Anything the core does not define travels in `nonportable_extensions`. See
https://github.com/apache/ossie/blob/main/core-spec/spec.md

    import qossie as O
    doc = O.export_datasets(model_doc)          # datasets and relationships
    O.validate(doc)                             # [] when the structure is sound
    lite = O.sqlite_copy(con, model_doc)        # the marts and the semantic sources, in SQLite
    O.run(doc, lite, "billed_amount", by=["bill.service_month"], dialect="SQLITE")
"""
from __future__ import annotations

import re
import sqlite3
from collections import deque

import pandas as pd

VERSION = "0.3.0.dev0"
VENDOR = "QAMAR_QSEM"
REF = re.compile(r"\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\b")


def _is_query(source: str) -> bool:
    return source.strip().lower().startswith("select")


def export_datasets(model_doc: dict) -> dict:
    """The Ossie document for the model's datasets and joins; metrics are added by the caller."""
    datasets, rels, ext = [], [], []
    for d in model_doc["datasets"]:
        out = {"name": d["name"], "source": f"sem_{d['name']}" if _is_query(d["source"]) else d["source"]}
        if d.get("primary_key"):
            out["primary_key"] = list(d["primary_key"])
        if d.get("description"):
            out["description"] = d["description"]
        out["fields"] = []
        for f in d["fields"]:
            field = {"name": f["name"], "expression": {"sql": f["sql"]}}
            if f.get("dialects"):
                field["expression"]["dialects"] = f["dialects"]
            if f.get("classification"):
                field["nonportable_extensions"] = [{"vendor_name": VENDOR, "data": {"classification": f["classification"]}}]
            out["fields"].append(field)
        if _is_query(d["source"]):
            out["nonportable_extensions"] = [{"vendor_name": VENDOR, "data": {"materialize_as": out["source"], "duckdb_sql": d["source"]}}]
        datasets.append(out)
        for j in d.get("joins", []):
            rel = {"name": f"{d['name']}_to_{j['to']}", "from": d["name"], "to": j["to"],
                   "from_columns": [a for a, _ in j["keys"]], "to_columns": [b for _, b in j["keys"]]}
            if j.get("asof"):
                rel["nonportable_extensions"] = [{"vendor_name": VENDOR, "data": {"asof_valid_between": j["asof"]}}]
                ext.append(f"relationship {rel['name']}: as-of validity join")
            rels.append(rel)
        if d.get("time"):
            rels.append({"name": f"{d['name']}_to_time", "from": d["name"], "to": "time",
                         "from_columns": [d["time"]], "to_columns": ["day"]})
    return {"version": VERSION, "name": model_doc["name"], "description": model_doc.get("description", ""),
            "datasets": datasets, "relationships": rels, "metrics": [], "nonportable_extensions": []}


def qualify(expr: str, dataset: str, field_names: set[str]) -> str:
    """Prefix the dataset's field names in an expression: amount_due -> bill.amount_due."""
    return re.sub(r"(?<![\w.])([a-z_][a-z0-9_]*)\b(?!\s*\()",
                  lambda m: f"{dataset}.{m.group(1)}" if m.group(1) in field_names else m.group(1), expr)


def validate(doc: dict) -> list[str]:
    """Structural checks of an Ossie document: required keys, unique names, references that resolve."""
    errs = []
    for k in ("version", "name", "datasets"):
        if not doc.get(k):
            errs.append(f"missing {k}")
    if doc.get("version") != VERSION:
        errs.append(f"version should be {VERSION}")
    fields = {}
    for d in doc.get("datasets", []):
        if d["name"] in fields:
            errs.append(f"dataset {d['name']} declared twice")
        if not d.get("source"):
            errs.append(f"dataset {d['name']}: no source")
        names = [f["name"] for f in d.get("fields", [])]
        if len(names) != len(set(names)):
            errs.append(f"dataset {d['name']}: a field name repeats")
        for f in d.get("fields", []):
            e = f.get("expression", {})
            if not (e.get("sql") or e.get("dialects")):
                errs.append(f"field {d['name']}.{f['name']}: no expression")
        fields[d["name"]] = set(names)
    for r in doc.get("relationships", []):
        for side, cols in (("from", "from_columns"), ("to", "to_columns")):
            if r[side] not in fields:
                errs.append(f"relationship {r['name']}: unknown dataset {r[side]}")
            elif not set(r[cols]) <= fields[r[side]]:
                errs.append(f"relationship {r['name']}: {cols} not declared in {r[side]}")
        if len(r["from_columns"]) != len(r["to_columns"]):
            errs.append(f"relationship {r['name']}: column lists differ in length")
    seen = set()
    for m in doc.get("metrics", []):
        if m["name"] in seen:
            errs.append(f"metric {m['name']} declared twice")
        seen.add(m["name"])
        for ds, f in REF.findall(m.get("expression", {}).get("sql", "")):
            if ds not in fields or f not in fields[ds]:
                errs.append(f"metric {m['name']}: {ds}.{f} is not a declared field")
    return errs


# ------------------------------------------------------------------------------ a second engine
def sqlite_copy(con, model_doc: dict) -> sqlite3.Connection:
    """An in-memory SQLite database with each dataset's source: tables copied, query sources materialized."""
    lite = sqlite3.connect(":memory:")
    for d in model_doc["datasets"]:
        name = f"sem_{d['name']}" if _is_query(d["source"]) else d["source"]
        sql = d["source"] if _is_query(d["source"]) else f"SELECT * FROM {d['source']}"
        try:
            df = con.execute(sql).df()
        except Exception:  # a source that is not built in this session (the session table) is skipped
            continue
        for c in df.columns:  # dates as ISO text and booleans as 0 or 1: SQLite has neither type
            first = df[c].dropna().iloc[0] if df[c].notna().any() else None
            if str(df[c].dtype).startswith("datetime") or hasattr(first, "isoformat"):
                df[c] = pd.to_datetime(df[c]).dt.strftime("%Y-%m-%d")
            elif str(df[c].dtype) == "bool":
                df[c] = df[c].astype(int)
        df.to_sql(name, lite, index=False)
    return lite


def _expr(field: dict, dialect: str) -> str:
    for alt in field["expression"].get("dialects", []) or []:
        if alt.get("dialect") == dialect:
            return alt["expression"]
    return field["expression"]["sql"]


def compile_sql(doc: dict, metric: str, by: list[str] | None = None, dialect: str = "SQLITE") -> str:
    """SQL for one model-scoped metric grouped by dataset.field references, for the given dialect."""
    by = list(by or [])
    ds = {d["name"]: d for d in doc["datasets"]}
    m = next(x for x in doc["metrics"] if x["name"] == metric)
    expr = m["expression"]["sql"]
    roots = list(dict.fromkeys(a for a, _ in REF.findall(expr)))
    root = roots[0]
    edges: dict[str, list] = {}
    for r in doc["relationships"]:
        edges.setdefault(r["from"], []).append(r)
    needed = list(dict.fromkeys([a for a in roots[1:]] + [b.split(".")[0] for b in by]))

    def path(target):
        q, seen = deque([(root, [])]), {root}
        while q:
            node, p = q.popleft()
            if node == target:
                return p
            for r in edges.get(node, []):
                if r["to"] not in seen:
                    seen.add(r["to"])
                    q.append((r["to"], p + [r]))
        raise ValueError(f"no relationship path from {root} to {target}")

    def sub(name):
        cols = ", ".join(f"{_expr(f, dialect)} AS {f['name']}" for f in ds[name]["fields"])
        return f"(SELECT {cols} FROM {ds[name]['source']}) AS {name}"

    joined, joins = {root}, []
    for t in needed:
        if t == root:
            continue
        for r in path(t):
            if r["to"] in joined:
                continue
            on = " AND ".join(f"{r['from']}.{a} = {r['to']}.{b}" for a, b in zip(r["from_columns"], r["to_columns"]))
            joins.append(f"LEFT JOIN {sub(r['to'])} ON {on}")
            joined.add(r["to"])
    sel = [f'{b} AS "{b}"' for b in by] + [f'{expr} AS "{metric}"']
    sql = f"SELECT {', '.join(sel)}\nFROM {sub(root)}\n" + "\n".join(joins)
    if by:
        sql += "\nGROUP BY " + ", ".join(str(i + 1) for i in range(len(by))) + "\nORDER BY 1"
    return sql


def run(doc: dict, lite: sqlite3.Connection, metric: str, by: list[str] | None = None, dialect: str = "SQLITE") -> pd.DataFrame:
    return pd.read_sql_query(compile_sql(doc, metric, by, dialect), lite)
