"""qamar_mcp: the Qamar semantic layer as a Model Context Protocol server over standard input and output.

Standard library plus the course's own modules; no SDK. Messages are JSON-RPC 2.0, one per line
(MCP specification 2025-11-25, stdio transport). Three tools:

    list_metrics     the certified metrics, with label, unit, version and description
    describe_metric  one metric in full
    query_metrics    metrics by fields with filters, run with the caller's role

The role comes from the credential, never from the request. With the stdio transport the credential
comes from the environment (the specification says stdio servers take credentials from the
environment): QAMAR_TOKEN is looked up, as a SHA-256 digest, in data/access/tokens.yaml.

    QAMAR_TOKEN=demo-eas-4082 uv run python servers/qamar_mcp.py      # from labs/

In a notebook, QamarServer(role).handle(message) answers one message without a process.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LABS))
import qamar as Q  # noqa: E402
import qsem as S  # noqa: E402

PROTOCOL = "2025-11-25"
SERVER = {"name": "qamar-semantic-layer", "version": "1.0.0"}

TOOLS = [
    {"name": "list_metrics", "title": "List certified metrics",
     "description": "The certified metrics of Qamar Telecom with label, unit, version and description.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "describe_metric", "title": "Describe a metric",
     "description": "One certified metric in full: definition, owner, version, synonyms.",
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"], "additionalProperties": False}},
    {"name": "query_metrics", "title": "Query certified metrics",
     "description": "Certified metrics grouped by fields (dataset.field) with SQL filters on fields. Runs with the caller's role.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["metrics"],
                     "properties": {"metrics": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                                    "by": {"type": "array", "items": {"type": "string"}},
                                    "where": {"type": "array", "items": {"type": "string"}}}},
     "outputSchema": {"type": "object", "properties": {"role": {"type": "string"}, "rows": {"type": "array"}}, "required": ["role", "rows"]}},
]


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def resolve_role(token: str | None, registry: dict | None = None) -> str | None:
    """The role a credential maps to, or None. Compares digests in constant time."""
    if not token:
        return None
    registry = registry if registry is not None else Q.yaml_load("data/access/tokens.yaml")["tokens"]
    d = digest(token)
    for known, role in registry.items():
        if hmac.compare_digest(known, d):
            return role
    return None


class QamarServer:
    def __init__(self, role: str | None, con=None):
        self.role = role
        policy = Q.yaml_load("data/access/policy_governed.yaml")
        base = S.Model.load(LABS / "data/semantic/qamar_model.yaml", con or Q.db(), metrics_dir=LABS / "data/metrics",
                            policy=policy, deny_by_default=True, lineage=True)
        self.model = base.as_role(role) if role else None

    # ---------------------------------------------------------------- JSON-RPC
    def handle(self, msg: dict) -> dict | None:
        """The response to one message, or None for a notification."""
        mid, method = msg.get("id"), msg.get("method", "")
        if mid is None:  # notifications (notifications/initialized and others) get no response
            return None
        try:
            if method == "initialize":
                if self.role is None:
                    return self._error(mid, -32001, "no valid credential: set QAMAR_TOKEN to a token in data/access/tokens.yaml")
                return self._ok(mid, {"protocolVersion": PROTOCOL, "capabilities": {"tools": {"listChanged": False}},
                                      "serverInfo": SERVER, "instructions": f"Answers run with the role {self.role}."})
            if method == "ping":
                return self._ok(mid, {})
            if self.role is None:
                return self._error(mid, -32001, "no valid credential")
            if method == "tools/list":
                return self._ok(mid, {"tools": TOOLS})
            if method == "tools/call":
                return self._ok(mid, self._call(msg.get("params", {})))
            return self._error(mid, -32601, f"method not found: {method}")
        except _BadParams as e:
            return self._error(mid, -32602, str(e))

    def _call(self, params: dict) -> dict:
        name, args = params.get("name"), params.get("arguments", {}) or {}
        tool = next((t for t in TOOLS if t["name"] == name), None)
        if tool is None:
            raise _BadParams(f"unknown tool: {name}")
        allowed = set(tool["inputSchema"]["properties"])
        extra = set(args) - allowed
        if extra:  # e.g. a "role" argument: the role is never taken from the request
            return self._tool_error(f"unexpected arguments {sorted(extra)}; the role comes from the credential only")
        certified = {n: m for n, m in self.model.metrics.items() if m.get("status") == "certified" and m.get("dataset") != "usage_event"}
        if name == "list_metrics":
            rows = [{k: self.model.describe(n)[k] for k in ("name", "label", "unit", "version")} for n in certified]
            return self._result({"role": self.role, "rows": rows})
        if name == "describe_metric":
            if args.get("name") not in certified:
                return self._tool_error(f"{args.get('name')!r} is not a certified metric")
            m = certified[args["name"]]
            return self._result({"role": self.role, "rows": [dict(self.model.describe(m["name"]), ai=m.get("ai", {}))]})
        mets = args.get("metrics", [])
        if not mets or any(x not in certified for x in mets):
            return self._tool_error(f"not certified or unknown: {[x for x in mets if x not in certified] or 'none given'}")
        try:
            df = self.model.query(mets, by=args.get("by", []), where=args.get("where", []))
        except S.SemanticError as e:  # includes AccessDenied
            return self._tool_error(str(e))
        except Exception as e:  # noqa: BLE001 - a bad filter is the caller's error, reported as a tool result
            return self._tool_error(f"query failed: {str(e).splitlines()[0][:150]}")
        rows = json.loads(df.head(500).to_json(orient="records", date_format="iso"))
        return self._result({"role": self.role, "rows": rows})

    # ---------------------------------------------------------------- shapes
    @staticmethod
    def _result(structured: dict) -> dict:
        return {"content": [{"type": "text", "text": json.dumps(structured, ensure_ascii=False)}],
                "structuredContent": structured, "isError": False}

    @staticmethod
    def _tool_error(text: str) -> dict:
        return {"content": [{"type": "text", "text": text}], "isError": True}

    @staticmethod
    def _ok(mid, result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    @staticmethod
    def _error(mid, code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


class _BadParams(Exception):
    pass


def main() -> None:
    os.chdir(LABS)
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stdin.reconfigure(encoding="utf-8")
    server = QamarServer(resolve_role(os.environ.get("QAMAR_TOKEN")))
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            out = server.handle(msg)
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
