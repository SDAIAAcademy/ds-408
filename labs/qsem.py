"""qsem: the course's small semantic layer over DuckDB (a stand-in for MetricFlow or Cube).

A model is a YAML document (data/semantic/qamar_model.yaml): datasets with fields and many-to-one
joins, and metrics. Metric files (data/metrics/*.yml) add or replace metrics. A query names metrics,
the fields to group by ("customer.region", "time.month") and filters; qsem compiles one aggregate
per metric component on its own dataset, then joins the results on the group-by keys (drill-across),
so a metric is never multiplied by a join to another fact.

    import qsem as S
    m = S.Model.load("data/semantic/qamar_model.yaml", con, metrics_dir="data/metrics")
    m.query(["billed_amount", "collection_rate"], by=["time.month"], where=["customer.segment = 'government'"])
    print(m.sql(["billed_amount"], by=["customer.region"]))

Metric types: simple (agg over an expression of one dataset, optional filter), ratio (numerator and
denominator are metrics, divided after aggregation), cumulative (a simple metric summed to date
within the fiscal year; needs time.month in by), derived (an expression over other metrics).

Access: Model(..., policy=dict, role="name") applies the role's row rule to every dataset a
component aggregates, and masks fields classified Restricted for roles without clearance.
"""
from __future__ import annotations

import copy
import re
from collections import deque
from pathlib import Path

import pandas as pd
import yaml

REF = re.compile(r"\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\b")
ADDITIVE = {"sum", "count"}
MASK = "'***'"


class SemanticError(Exception):
    pass


class AccessDenied(SemanticError):
    pass


def _key(ref: str) -> str:
    return ref.replace(".", "__")


def load_yaml(path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_metrics(folder) -> list[dict]:
    out = []
    for f in sorted(Path(folder).glob("*.yml")):
        doc = load_yaml(f)
        out.extend(doc if isinstance(doc, list) else [doc])
    return out


class Model:
    def __init__(self, doc: dict, con, policy: dict | None = None, role: str | None = None,
                 lineage: bool = False, deny_by_default: bool = False):
        self.doc = copy.deepcopy(doc)
        self.con = con
        self.datasets = {d["name"]: d for d in self.doc["datasets"]}
        self.metrics = {m["name"]: m for m in self.doc.get("metrics", [])}
        self.policy = policy
        self.role = role
        self.lineage = lineage  # classify a field by the source columns it reads, not only by its tag
        self.deny_by_default = deny_by_default  # a dataset without a row rule is refused for a limited role
        self.preaggs: dict[str, dict] = {}
        if role and (not policy or role not in policy["roles"]):
            raise AccessDenied(f"unknown role {role!r}")

    # ------------------------------------------------------------------ building
    @classmethod
    def load(cls, path, con, metrics_dir=None, **kw) -> "Model":
        doc = load_yaml(path)
        if metrics_dir:
            doc = with_metrics(doc, load_metrics(metrics_dir))
        return cls(doc, con, **kw)

    def as_role(self, role: str | None, **kw) -> "Model":
        m = Model(self.doc, self.con, policy=kw.get("policy", self.policy), role=role,
                  lineage=kw.get("lineage", self.lineage), deny_by_default=kw.get("deny_by_default", self.deny_by_default))
        m.preaggs = self.preaggs
        return m

    # ------------------------------------------------------------------ fields and classification
    def field(self, ds: str, name: str) -> dict:
        try:
            return next(f for f in self.datasets[ds]["fields"] if f["name"] == name)
        except (KeyError, StopIteration):
            raise SemanticError(f"unknown field {ds}.{name}") from None

    def restricted_columns(self) -> set[str]:
        reg = (self.policy or {}).get("classification", {})
        return {k for k, v in reg.items() if v == "Restricted"}

    def is_restricted(self, ds: str, f: dict) -> bool:
        if f.get("classification") == "Restricted":
            return True
        if self.lineage:
            src = self.datasets[ds]["source"]
            cols = set(re.findall(r"[a-z_][a-z0-9_]*", f["sql"]))
            return any(f"{src}.{c}" in self.restricted_columns() for c in cols)
        return False

    def _clear(self) -> bool:
        return not self.role or bool(self.policy["roles"][self.role].get("restricted", False))

    def _subquery(self, ds: str) -> str:
        d = self.datasets[ds]
        cols = []
        for f in d["fields"]:
            expr = MASK if (not self._clear() and self.is_restricted(ds, f)) else f["sql"]
            cols.append(f"{expr} AS {f['name']}")
        src = d["source"]
        src = f"({src})" if src.strip().lower().startswith("select") else src
        return f"(SELECT {', '.join(cols)} FROM {src})"

    # ------------------------------------------------------------------ joins
    def _edges(self, ds: str):
        d = self.datasets[ds]
        for j in d.get("joins", []):
            yield j["to"], j
        if d.get("time"):
            yield "time", {"to": "time", "keys": [[d["time"], "day"]]}

    def path(self, root: str, target: str) -> list[tuple[str, str, dict]]:
        """Many-to-one join path from root to target: [(from, to, join), ...]."""
        seen, q = {root}, deque([(root, [])])
        while q:
            node, p = q.popleft()
            if node == target:
                return p
            for nxt, j in self._edges(node):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, p + [(node, nxt, j)]))
        raise SemanticError(f"no many-to-one path from {root} to {target}")

    # ------------------------------------------------------------------ access
    def _row_rule(self, ds: str) -> str | None:
        if not self.role:
            return None
        r = self.policy["roles"][self.role]
        regions = r.get("regions", "all")
        if regions == "all":
            return None
        rule = self.policy.get("row_rules", {}).get(ds)
        if rule is None:
            if self.deny_by_default:
                raise AccessDenied(f"role {self.role} has no row rule for dataset {ds}")
            return None
        values = ", ".join(f"'{v}'" for v in regions)
        return f"{rule} IN ({values})"

    # ------------------------------------------------------------------ compiling
    def _component(self, metric: dict, by: list[str], where: list[str]) -> str:
        root = metric["dataset"]
        rule = self._row_rule(root)
        conds = list(where) + ([rule] if rule else [])
        pre = self._preagg_for(metric, by, conds)
        if pre:
            return pre
        refs = [r for r in by] + [m.group(0) for c in conds for m in REF.finditer(c)]
        needed = {r.split(".")[0] for r in refs} - {root}
        alias = {root: "d0"}
        joins = []
        for t in sorted(needed):
            if t not in self.datasets:
                raise SemanticError(f"unknown dataset {t}")
            for a, b, j in self.path(root, t):
                if b in alias:
                    continue
                alias[b] = f"d{len(alias)}"
                on = " AND ".join(f"{alias[a]}.{x} = {alias[b]}.{y}" for x, y in j["keys"])
                if j.get("asof"):  # type 2 history: the row valid on the fact's date, or the current row
                    t0 = self.datasets[root].get("time")
                    on += (f" AND d0.{t0} BETWEEN {alias[b]}.{j['asof'][0]} AND {alias[b]}.{j['asof'][1]}" if t0
                           else f" AND {alias[b]}.{j['asof'][1]} = DATE '9999-12-31'")
                joins.append(f"LEFT JOIN {self._subquery(b)} {alias[b]} ON {on}")

        def res(expr: str) -> str:
            def sub(m):
                ds, f = m.group(1), m.group(2)
                if ds not in alias:
                    return m.group(0)
                self.field(ds, f)
                return f"{alias[ds]}.{f}"
            return REF.sub(sub, expr)

        fields = {f["name"] for f in self.datasets[root]["fields"]}
        expr = re.sub(r"\b([a-z_][a-z0-9_]*)\b", lambda m: f"d0.{m.group(1)}" if m.group(1) in fields else m.group(1),
                      metric["expr"])
        agg = metric["agg"].lower()
        aggsql = f"COUNT(DISTINCT {expr})" if agg == "count_distinct" else f"{agg.upper()}({expr})"
        if metric.get("filter"):
            filt = re.sub(r"\b([a-z_][a-z0-9_]*)\b", lambda m: f"d0.{m.group(1)}" if m.group(1) in fields else m.group(1),
                          metric["filter"])
            aggsql += f" FILTER (WHERE {filt})"
        sel = [f"{res(r)} AS {_key(r)}" for r in by] + [f"{aggsql} AS {metric['name']}"]
        sql = f"SELECT {', '.join(sel)}\nFROM {self._subquery(root)} d0\n" + "\n".join(joins)
        if conds:
            sql += "\nWHERE " + " AND ".join(f"({res(c)})" for c in conds)
        if by:
            sql += "\nGROUP BY " + ", ".join(str(i + 1) for i in range(len(by)))
        return sql

    def _expand(self, name: str, out: dict, by: list[str]):
        """Collect the simple components a metric needs, in out[name] = (metric, by)."""
        m = self.metrics.get(name)
        if m is None:
            raise SemanticError(f"unknown metric {name!r}")
        t = m.get("type", "simple")
        if t == "simple":
            out.setdefault(name, (m, by))
        elif t == "ratio":
            self._expand(m["numerator"], out, by)
            self._expand(m["denominator"], out, by)
        elif t == "derived":
            for i in m["inputs"]:
                self._expand(i, out, by)
        elif t == "cumulative":
            if "time.month" not in by:
                raise SemanticError(f"{name} is cumulative: group by time.month")
            fy_by = by + ([] if "time.fiscal_year" in by else ["time.fiscal_year"])
            base = self.metrics[m["base"]]
            out.setdefault(m["base"] + "__fy", (dict(base, name=m["base"] + "__fy"), fy_by))
        else:
            raise SemanticError(f"unknown metric type {t}")

    def _final(self, name: str, by: list[str]) -> str:
        m = self.metrics[name]
        t = m.get("type", "simple")
        if t == "simple":
            return name
        if t == "ratio":
            return f"CAST({self._final(m['numerator'], by)} AS DOUBLE) / NULLIF({self._final(m['denominator'], by)}, 0)"
        if t == "derived":
            expr = m["expr"]
            for i in sorted(m["inputs"], key=len, reverse=True):
                expr = re.sub(rf"\b{i}\b", f"({self._final(i, by)})", expr)
            return expr
        if t == "cumulative":
            part = [_key(r) for r in by if r != "time.month"] + (["time__fiscal_year"] if "time.fiscal_year" not in by else [])
            return (f"SUM({m['base']}__fy) OVER (PARTITION BY {', '.join(part)} ORDER BY time__month "
                    f"ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)")
        raise SemanticError(t)

    def sql(self, metrics: list[str], by: list[str] | None = None, where: list[str] | None = None) -> str:
        by, where = list(by or []), list(where or [])
        comps: dict = {}
        for name in metrics:
            self._expand(name, comps, by)
        ctes, keysets = [], []
        for i, (cname, (m, cby)) in enumerate(comps.items()):
            ctes.append(f"c{i} AS (\n{self._component(m, cby, where)}\n)")
            keysets.append([_key(r) for r in cby])
        allkeys = [k for k in dict.fromkeys(k for ks in keysets for k in ks)]
        frm = "c0"
        for i in range(1, len(ctes)):
            shared = [k for k in keysets[i] if k in keysets[0]]
            frm += f" FULL JOIN c{i} USING ({', '.join(shared)})" if shared else f" CROSS JOIN c{i}"
        sel = [f"{k} AS \"{k.replace('__', '.')}\"" for k in allkeys if k.replace("__", ".") in by]
        sel += [f"{self._final(n, by)} AS \"{n}\"" for n in metrics]
        order = f"\nORDER BY {', '.join(str(i + 1) for i in range(len(by)))}" if by else ""
        return "WITH " + ",\n".join(ctes) + f"\nSELECT {', '.join(sel)}\nFROM {frm}{order}"

    def query(self, metrics: list[str], by: list[str] | None = None, where: list[str] | None = None) -> pd.DataFrame:
        return self.con.execute(self.sql(metrics, by, where)).df()

    def value(self, metric: str, where: list[str] | None = None) -> float:
        return float(self.query([metric], [], where).iloc[0, 0])

    # ------------------------------------------------------------------ pre-aggregations
    def materialize(self, preaggs: list[dict]) -> dict[str, int]:
        """Create one table per pre-aggregation (simple, additive metrics only) and route matching queries to it."""
        rows = {}
        for p in preaggs:
            for name in p["measures"]:
                mm = self.metrics[name]
                if mm.get("type", "simple") != "simple" or mm["agg"].lower() not in ADDITIVE:
                    raise SemanticError(f"{name} cannot roll up from a pre-aggregation (not a sum or count)")
                if mm["dataset"] != p["dataset"]:
                    raise SemanticError(f"{name} is not on dataset {p['dataset']}")
            saved, self.preaggs = self.preaggs, {}
            self.con.execute(f"CREATE OR REPLACE TABLE pre_{p['name']} AS " + Model(self.doc, self.con).sql(p["measures"], p["by"]))
            self.preaggs = saved
            self.preaggs[p["name"]] = p
            rows[p["name"]] = self.con.execute(f"SELECT count(*) FROM pre_{p['name']}").fetchone()[0]
        return rows

    def _preagg_for(self, metric: dict, by: list[str], conds: list[str]) -> str | None:
        refs = set(by) | {m.group(0) for c in conds for m in REF.finditer(c)}
        for p in self.preaggs.values():
            if (p["dataset"] == metric["dataset"] and metric["name"] in p["measures"] and refs <= set(p["by"])
                    and metric["agg"].lower() in ADDITIVE):
                def res(expr):
                    return REF.sub(lambda m: f'"{m.group(0)}"', expr)
                sel = [f'"{r}" AS {_key(r)}' for r in by] + [f"SUM({metric['name']}) AS {metric['name']}"]
                sql = f"SELECT {', '.join(sel)} FROM pre_{p['name']}"
                if conds:
                    sql += " WHERE " + " AND ".join(f"({res(c)})" for c in conds)
                if by:
                    sql += " GROUP BY " + ", ".join(str(i + 1) for i in range(len(by)))
                return sql
        return None

    def plan(self, metrics: list[str], by: list[str] | None = None, where: list[str] | None = None) -> list[dict]:
        """Which table each simple component of a query reads, and how many rows that table has."""
        by, where = list(by or []), list(where or [])
        comps: dict = {}
        for name in metrics:
            self._expand(name, comps, by)
        out = []
        for cname, (m, cby) in comps.items():
            rule = self._row_rule(m["dataset"])
            conds = where + ([rule] if rule else [])
            refs = set(cby) | {x.group(0) for c in conds for x in REF.finditer(c)}
            pre = next((p for p in self.preaggs.values() if p["dataset"] == m["dataset"] and m["name"] in p["measures"]
                        and refs <= set(p["by"]) and m["agg"].lower() in ADDITIVE), None)
            table = f"pre_{pre['name']}" if pre else self.datasets[m["dataset"]]["source"]
            if table.strip().lower().startswith("select"):
                table = f"({table})"
            rows = self.con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            out.append({"component": cname, "reads": f"pre_{pre['name']}" if pre else m["dataset"], "rows": rows})
        return out

    # ------------------------------------------------------------------ describing
    def describe(self, name: str) -> dict:
        m = self.metrics[name]
        return {k: m.get(k) for k in ("name", "label", "type", "version", "status", "owner", "unit", "description")}

    def catalogue(self) -> pd.DataFrame:
        return pd.DataFrame([self.describe(n) for n in self.metrics])


def run_tests(model: Model, names: list[str] | None = None, tolerance: float = 1e-6) -> pd.DataFrame:
    """Run each metric's reconciliation tests: the metric over all data against an independent SQL total."""
    rows = []
    for name in names or list(model.metrics):
        for t in model.metrics[name].get("tests", []) or []:
            if "reconcile" not in t:
                continue
            expected = model.con.execute(t["reconcile"]).fetchone()[0]
            try:
                actual = model.value(name, t.get("where"))
            except Exception as e:  # a test that cannot run is a failed test
                actual, err = None, str(e)[:80]
            else:
                err = ""
            ok = actual is not None and expected is not None and abs(float(actual) - float(expected)) <= tolerance * max(1, abs(float(expected)))
            rows.append({"metric": name, "test": "reconcile", "expected": expected, "actual": actual, "passed": ok, "error": err})
    return pd.DataFrame(rows)


def with_metrics(doc: dict, metrics: list[dict]) -> dict:
    """A copy of the model document whose metrics are replaced or added by name."""
    doc = copy.deepcopy(doc)
    byname = {m["name"]: m for m in doc.get("metrics", [])}
    for m in metrics:
        byname[m["name"]] = m
    doc["metrics"] = list(byname.values())
    return doc
