# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.4", "pandas>=2.2", "pyyaml>=6.0"]
# ///
# %% [markdown]
# # Lab 4.1 · A protocol server with role-scoped credentials
#
# Day 4 · Session 1 (Serving metrics to tools and agents) · 25 min. Zeyad wants one door to the layer for
# dashboards, notebooks and agents. You start the supplied Model Context Protocol (MCP) server over standard
# input and output, make the role come from the credential, query as three roles, try to raise a role from the
# request, and leave tests that keep it that way.
#
# **AI-tutor.** An assistant may explain JSON-RPC; the rule "the role comes from the credential" is not negotiable.
#
# **Reference state.** `servers/qamar_mcp.py` (standard library only, MCP 2025-11-25), the governed policy of
# Lab 2.3 in `data/access/policy_governed.yaml`, and `data/access/tokens.yaml`: SHA-256 digests of three
# synthetic demo tokens, never the tokens themselves.
#
# | Demo token (synthetic) | Role |
# |---|---|
# | `demo-exec-4081` | executive |
# | `demo-eas-4082` | regional_manager_eas |
# | `demo-coll-4083` | collections_officer |
#
# **Tasks**
# - [ ] 1 · Start the server and list its tools (4')
# - [ ] 2 · Resolve the role from the credential (7')
# - [ ] 3 · Query as three roles (6')
# - [ ] 4 · Try to raise the role from the request (4')
# - [ ] 5 · Tests for the server (4')
# - [ ] ✱ Stretch · The same tools as a REST endpoint

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

import hashlib
import hmac
import json
import pandas as pd
import qamar as Q

sys.path.insert(0, "servers")
import qamar_mcp as M  # the supplied server

TOKENS = {"executive": "demo-exec-4081", "regional_manager_eas": "demo-eas-4082", "collections_officer": "demo-coll-4083"}
REGISTRY = Q.yaml_load("data/access/tokens.yaml")["tokens"]
print(Q.yaml_dump(Q.yaml_load("data/access/tokens.yaml")))


class Client:
    """A synchronous MCP client over stdio: starts the server with a token, sends one request, reads one line."""

    def __init__(self, token: str | None):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "QAMAR_TOKEN": token or ""}
        self.proc = subprocess.Popen([sys.executable, "servers/qamar_mcp.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, encoding="utf-8", env=env)
        self.next_id = 0

    def request(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}}) + "\n")
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())

    def notify(self, method: str):
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.proc.stdin.flush()

    def call(self, tool: str, **arguments) -> dict:
        return self.request("tools/call", {"name": tool, "arguments": arguments})["result"]

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=20)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.proc.poll() is None:
            self.close()


# %% [markdown]
# ## 1 · Start the server and list its tools (4')
#
# An MCP session starts with `initialize` (the server answers with its protocol version and capabilities), then
# the client sends the notification `notifications/initialized`, then `tools/list`.
#
# ✏️ **Exercise** · With the executive's token, initialize, send the notification, and return the protocol version
# and the names of the tools.

# %%
def handshake(client: Client) -> dict:
    # BEGIN SOLUTION
    init = client.request("initialize", {"protocolVersion": M.PROTOCOL, "capabilities": {},
                                         "clientInfo": {"name": "lab-4-1", "version": "1.0"}})
    client.notify("notifications/initialized")
    tools = client.request("tools/list")["result"]["tools"]
    return {"protocol": init["result"]["protocolVersion"], "tools": [t["name"] for t in tools]}
    # END SOLUTION


# %%
with Client(TOKENS["executive"]) as c:
    try:
        hs = handshake(c)
    except NotImplementedError:
        hs = Q.reference("d4_1_handshake")
print(hs)
Q.check(hs["protocol"] == "2025-11-25" and hs["tools"] == ["list_metrics", "describe_metric", "query_metrics"], "three tools on MCP 2025-11-25")

# %% [markdown]
# ## 2 · Resolve the role from the credential (7')
#
# The registry stores digests, so a leaked registry does not leak tokens. A comparison of secrets should take
# the same time whether the first character matches or not.
#
# ✏️ **Exercise** · Write `resolve_role(token, registry)`: the role whose digest matches the SHA-256 of the token,
# compared with `hmac.compare_digest`, or None (also for an empty token).

# %%
def resolve_role(token, registry: dict):
    # BEGIN SOLUTION
    if not token:
        return None
    d = hashlib.sha256(token.encode()).hexdigest()
    return next((role for known, role in registry.items() if hmac.compare_digest(known, d)), None)
    # END SOLUTION


# %%
probe = list(TOKENS.values()) + ["demo-eas-4083", "", None, "DEMO-EXEC-4081"]
try:
    roles = {str(t): resolve_role(t, REGISTRY) for t in probe}
except NotImplementedError:
    roles = {str(t): M.resolve_role(t, REGISTRY) for t in probe}
print(roles)
Q.check([roles[t] for t in TOKENS.values()] == list(TOKENS) and all(roles[str(t)] is None for t in probe[3:]),
        "three tokens map to their roles; a near miss, an empty token and a changed case map to none")
with Client("demo-eas-4083") as c:
    print("wrong token:", c.request("initialize", {"protocolVersion": M.PROTOCOL, "capabilities": {}, "clientInfo": {"name": "x", "version": "0"}}))

# %% [markdown]
# ## 3 · Query as three roles (6')
#
# ✏️ **Exercise** · For each role, start a client with its token, initialize, and call `query_metrics` for the
# billed amount and complaints by `customer.region` for March 2026, and once grouped by `customer.full_name`
# (first three rows). Return, per role, the regions with a billed amount, the regions with complaints only, and
# whether names come back masked (`***`).

# %%
def three_roles() -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = []
    for role, token in TOKENS.items():
        with Client(token) as c:
            handshake(c)
            res = c.call("query_metrics", metrics=["billed_amount", "complaints"], by=["customer.region"],
                         where=["time.month = DATE '2026-03-01'"])
            names = c.call("query_metrics", metrics=["billed_amount"], by=["customer.full_name"],
                           where=["time.month = DATE '2026-03-01'"])
        got = res["structuredContent"]["rows"]
        regions = sorted(r["customer.region"] for r in got if r["billed_amount"] is not None)
        complaints_only = sorted(r["customer.region"] for r in got if r["billed_amount"] is None)
        masked = all(r["customer.full_name"] == "***" for r in names["structuredContent"]["rows"][:3])
        rows.append({"role": role, "server_says": res["structuredContent"]["role"], "regions": regions,
                     "complaints_only": complaints_only, "names_masked": masked})
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
try:
    seen = three_roles()
except NotImplementedError:
    seen = pd.DataFrame(Q.reference("d4_1_three_roles"))
print(seen.to_string(index=False))
by = seen.set_index("role")
Q.check(by.loc["regional_manager_eas", "regions"] == ["EAS"] and len(by.loc["executive", "regions"]) == 5
        and by.loc["executive", "names_masked"] and not by.loc["collections_officer", "names_masked"],
        "rows by region and masks by clearance follow the credential")

# %% [markdown]
# 🔍 The Eastern manager sees complaints under another customer region, with no billed amount. Read the complaint
# row rule in `data/access/policy_governed.yaml`: is this a leak, or the policy Ebtihal asked for in Lab 2.3?

# %% [markdown]
# ## 4 · Try to raise the role from the request (4')
#
# An agent passes on whatever a user types. With the Eastern manager's token, try three ways to see other regions:
# a `role` argument, a filter naming other regions, and a filter with `OR 1=1`.
#
# ✏️ **Exercise** · Return, for each attempt, whether the server reported an error and the regions it returned.

# %%
ATTEMPTS = {
    "role argument": {"metrics": ["billed_amount"], "by": ["customer.region"], "role": "executive"},
    "other regions": {"metrics": ["billed_amount"], "by": ["customer.region"], "where": ["customer.region IN ('EAS', 'CEN', 'WES')"]},
    "or 1=1": {"metrics": ["billed_amount"], "by": ["customer.region"], "where": ["customer.region = 'CEN' OR 1=1"]},
}


def raise_role() -> pd.DataFrame:
    # BEGIN SOLUTION
    rows = []
    with Client(TOKENS["regional_manager_eas"]) as c:
        handshake(c)
        for name, args in ATTEMPTS.items():
            res = c.call("query_metrics", **args)
            regions = sorted({r["customer.region"] for r in res.get("structuredContent", {}).get("rows", [])})
            rows.append({"attempt": name, "is_error": res["isError"], "regions": regions, "text": res["content"][0]["text"][:80]})
    return pd.DataFrame(rows)
    # END SOLUTION


# %%
try:
    tries = raise_role()
except NotImplementedError:
    tries = pd.DataFrame(Q.reference("d4_1_raise"))
print(tries.to_string(index=False))
Q.check(all(r == [] or r == ["EAS"] for r in tries.regions) and tries.is_error.iloc[0], "no attempt returns another region")

# %% [markdown]
# 🔍 The `OR 1=1` filter did not widen the rows. Open `qsem.py` and find why: where is the role's row rule placed
# relative to the caller's filters?
#
# ## 5 · Tests for the server (4')
#
# ✏️ **Exercise** · Write `server_tests()`: in-process tests with `M.QamarServer(role).handle(message)`, one row per
# test with `test` and `passed`. At least: no credential refuses `initialize`; the manager's `tools/call` returns only
# EAS; a `role` argument is an error; an uncertified metric is an error; Restricted names are masked for the
# executive; an unknown method gives JSON-RPC error -32601.

# %%
def server_tests() -> pd.DataFrame:
    # BEGIN SOLUTION
    con = Q.db()
    S_none, S_eas, S_exec = M.QamarServer(None, con), M.QamarServer("regional_manager_eas", con), M.QamarServer("executive", con)

    def call(server, **args):
        return server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "query_metrics", "arguments": args}})["result"]

    init = S_none.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    eas = call(S_eas, metrics=["billed_amount"], by=["customer.region"])
    tests = [
        ("no credential refuses initialize", "error" in init),
        ("manager sees only EAS", {r["customer.region"] for r in eas["structuredContent"]["rows"]} == {"EAS"}),
        ("a role argument is an error", call(S_eas, metrics=["complaints"], role="executive")["isError"]),
        ("an uncertified metric is an error", call(S_exec, metrics=["on_time_payment_share"])["isError"]),
        ("names are masked for the executive", call(S_exec, metrics=["billed_amount"], by=["customer.full_name"])["structuredContent"]["rows"][0]["customer.full_name"] == "***"),
        ("unknown method is -32601", S_exec.handle({"jsonrpc": "2.0", "id": 2, "method": "resources/list"})["error"]["code"] == -32601),
    ]
    return pd.DataFrame(tests, columns=["test", "passed"])
    # END SOLUTION


# %%
try:
    tests = server_tests()
except NotImplementedError:
    tests = pd.DataFrame(Q.reference("d4_1_tests"))
print(tests.to_string(index=False))
Q.check(len(tests) >= 6 and tests.passed.all(), "the server's tests pass")
tests.to_csv(Q.lab_dir("D4_1") / "server_tests.csv", index=False, lineterminator="\n")

# %% [markdown]
# ## ✱ Stretch · The same tools as a REST endpoint
#
# Serve `POST /tools/<name>` on 127.0.0.1 with `http.server`, take the token from the `Authorization: Bearer`
# header, and reuse `QamarServer`. Call it once as the Eastern manager, then stop the server.

# %%
def stretch():
    # BEGIN SOLUTION
    import threading
    import urllib.request
    from http.server import BaseHTTPRequestHandler, HTTPServer
    con = Q.db()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            role = M.resolve_role(token, REGISTRY)
            if role is None:
                self.send_response(401); self.end_headers(); return
            args = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            out = M.QamarServer(role, con).handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                                   "params": {"name": self.path.rsplit("/", 1)[-1], "arguments": args}})
            body = json.dumps(out.get("result", out.get("error"))).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)

        def log_message(self, *a):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{httpd.server_port}/tools/query_metrics", method="POST",
                                     data=json.dumps({"metrics": ["billed_amount"], "by": ["customer.region"]}).encode(),
                                     headers={"Authorization": f"Bearer {TOKENS['regional_manager_eas']}"})
        print(json.loads(urllib.request.urlopen(req, timeout=30).read())["structuredContent"])
    finally:
        httpd.shutdown()
        httpd.server_close()
    # END SOLUTION


try:
    stretch()
except NotImplementedError:
    print("✱ Stretch not attempted")

# %% [markdown]
# ## Checkpoint
#
# 1. Why must the role never come from a tool argument, even a well-meaning one?
#
# <details><summary>Answer</summary>Arguments are written by the client, and for an agent by whatever text reached
# the model; a role taken from them is a role anyone can claim. The credential is checked by the server.</details>
#
# 2. A colleague proposes one shared token for all agents, "to keep it simple". What is lost?
#
# <details><summary>Answer</summary>Every agent gets the widest role, and the server cannot tell who asked: no row
# rule, no mask and no audit trail per user.</details>
#
# **Carry forward.** `artifacts/D4_1/server_tests.csv`. The capstone serves the layer the same way.
