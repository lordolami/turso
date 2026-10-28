"""Check standalone design artifacts without building or opening Turso databases.

Uses only Python's standard library. The schema/example checker implements the
explicit keyword subset used here, not the entire JSON Schema specification.
Independent SQLite parsing checks catalog syntax, not Turso compatibility.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

from generate_standalone_contracts import REQUIREMENTS, REVISION, SOURCE_ROOT, extract_capabilities

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "standalone"
CONTRACTS = DOCS / "contracts"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> object:
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {path}: {key}")
            result[key] = value
        return result
    def no_nonfinite(value):
        raise ValueError(f"Non-finite JSON literal in {path}: {value}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates, parse_constant=no_nonfinite)


def resolve_ref(root: dict, ref: str) -> dict:
    require(ref.startswith("#/"), f"Only local schema references are supported: {ref}")
    item = root
    for part in ref[2:].split("/"):
        item = item[part.replace("~1", "/").replace("~0", "~")]
    return item


ANNOTATIONS = {"$schema", "$id", "title", "description", "writeOnly", "contentEncoding", "default", "examples"}
KEYWORDS = ANNOTATIONS | {"$defs", "$ref", "type", "const", "enum", "required", "properties", "additionalProperties", "items", "minItems", "maxItems", "minimum", "maximum", "minLength", "maxLength", "pattern", "anyOf", "oneOf"}


def check_schema(schema: dict, root: dict | None = None) -> None:
    root = root or schema
    require(isinstance(schema, dict), "Schema must be an object")
    require(not set(schema) - KEYWORDS, f"Unhandled schema keyword(s): {set(schema) - KEYWORDS}")
    if "$ref" in schema:
        resolve_ref(root, schema["$ref"])
    for field in ("$defs", "properties"):
        for child in schema.get(field, {}).values():
            check_schema(child, root)
    if "items" in schema:
        check_schema(schema["items"], root)
    for field in ("anyOf", "oneOf"):
        for child in schema.get(field, []):
            check_schema(child, root)
    require(set(schema.get("required", [])) <= set(schema.get("properties", {})), "Required schema field has no declaration")


def validate(value, schema: dict, root: dict | None = None, location: str = "$") -> None:
    root = root or schema
    if "$ref" in schema:
        validate(value, resolve_ref(root, schema["$ref"]), root, location)
    for field, expected in (("anyOf", None), ("oneOf", 1)):
        if field in schema:
            matches = 0
            for choice in schema[field]:
                try:
                    validate(value, choice, root, location)
                    matches += 1
                except ValueError:
                    pass
            require(matches > 0 if expected is None else matches == expected, f"{location}: invalid {field} choice")
    types = schema.get("type", [])
    if isinstance(types, str):
        types = [types]
    kind = "null" if value is None else "boolean" if isinstance(value, bool) else "integer" if isinstance(value, int) else "number" if isinstance(value, float) else "string" if isinstance(value, str) else "array" if isinstance(value, list) else "object" if isinstance(value, dict) else "unknown"
    require(not types or kind in types or (kind == "integer" and "number" in types), f"{location}: expected {types}, got {kind}")
    if "const" in schema:
        require(value == schema["const"] and isinstance(value, bool) == isinstance(schema["const"], bool), f"{location}: invalid constant")
    if "enum" in schema:
        require(any(value == choice and isinstance(value, bool) == isinstance(choice, bool) for choice in schema["enum"]), f"{location}: invalid enum value")
    if kind == "object":
        require(set(schema.get("required", [])) <= set(value), f"{location}: missing required fields")
        props = schema.get("properties", {})
        require(schema.get("additionalProperties", True) is not False or not set(value) - set(props), f"{location}: unknown fields {set(value) - set(props)}")
        for key, item in value.items():
            if key in props:
                validate(item, props[key], root, f"{location}.{key}")
    elif kind == "array":
        require(len(value) >= schema.get("minItems", 0), f"{location}: too few items")
        require(len(value) <= schema.get("maxItems", sys.maxsize), f"{location}: too many items")
        for n, item in enumerate(value):
            validate(item, schema.get("items", {}), root, f"{location}[{n}]")
    elif kind == "string":
        require(len(value) >= schema.get("minLength", 0), f"{location}: string too short")
        require(len(value) <= schema.get("maxLength", sys.maxsize), f"{location}: string too long")
        require("pattern" not in schema or re.search(schema["pattern"], value) is not None, f"{location}: pattern mismatch")
    elif kind in ("integer", "number"):
        require(value >= schema.get("minimum", float("-inf")), f"{location}: value too small")
        require(value <= schema.get("maximum", float("inf")), f"{location}: value too large")


def must_reject(value, schema: dict, label: str) -> None:
    try:
        validate(value, schema)
    except ValueError:
        return
    raise ValueError(f"Invalid example was accepted: {label}")


def heading_ids(text: str) -> set[str]:
    result, counts = set(), {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        result.add(slug if n == 0 else f"{slug}-{n}")
    return result


def check_links() -> tuple[int, int]:
    files = sorted(DOCS.rglob("*.md"))
    links = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        for raw in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
            dest = raw.strip().strip("<>")
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", dest):
                continue
            target, _, fragment = unquote(dest).partition("#")
            resolved = (path.parent / target).resolve() if target else path
            require(resolved.exists(), f"Broken link in {path.name}: {raw}")
            if fragment and resolved.suffix == ".md":
                require(fragment in heading_ids(resolved.read_text(encoding="utf-8")), f"Broken anchor in {path.name}: {raw}")
            links += 1
    require("docs/standalone/README.md" in (ROOT / "README.md").read_text(encoding="utf-8"), "Root README lacks design entry")
    return len(files), links


def check_operations() -> int:
    data = read_json(CONTRACTS / "operations.json")
    operations = data["operations"]
    ids, http, cli, mcp = set(), set(), set(), set()
    permissions = set(data["permissions"])
    for op in operations:
        for seen, key, label in [(ids, op["id"], "operation"), (http, (op["http"]["method"], op["http"]["path"]), "HTTP binding"),
                                  (cli, tuple(op["cli"]), "CLI binding"), (mcp, op["mcp"]["name"], "MCP binding")]:
            require(key not in seen, f"Duplicate {label}: {key}")
            seen.add(key)
        require(op["permission"] in permissions, f"Unknown permission: {op['id']}")
        require(set(op["interfaces"]) == {"http", "cli", "mcp", "dashboard"}, f"Parity gap: {op['id']}")
        require(re.fullmatch(r"mira_[a-z0-9_]+", op["mcp"]["name"]) is not None, "Invalid MCP name")
        require(len(op["mcp"]["name"]) <= 64, "MCP tool name too long")
        require(op["http"]["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"}, "Invalid HTTP method")
        require(op["job"] == (op["execution"] == "durable_job"), f"Job mismatch: {op['id']}")
        require(op["idempotency"] in {"read", "native_write_receipt_required", "durable_service_receipt"}, "Undefined retry semantics")
        require(not re.match(r"(cloud|cluster|shard|billing|collection|nosql)\.", op["id"]), "Excluded operation in registry")
        for schema in (op["input_schema"], op["output_schema"]):
            check_schema({"$defs": data["$defs"], **schema})
        selectors = set(re.findall(r"{([^}]+)}", op["http"]["path"]))
        require(selectors <= set(op["input_schema"]["required"]), f"Path selector missing: {op['id']}")
    required = {"databases.create", "query.execute", "schema.apply", "grants.create", "branches.create", "recovery.restore", "recovery.installation_restore", "sync.push", "jobs.cancel", "instance.capabilities"}
    require(required <= ids, "Required operation family missing")
    query = next(x for x in operations if x["id"] == "query.execute")
    query_input = {"$defs": data["$defs"], **query["input_schema"]}
    query_output = {"$defs": data["$defs"], **query["output_schema"]}
    validate({"database_id": "00000000-0000-7000-8000-000000000001", "expected_generation_id": "00000000-0000-7000-8000-000000000002", "sql": "SELECT ?", "mode": "read", "parameters": [{"type": "integer", "value": "9223372036854775807"}]}, query_input)
    must_reject({"sql": "SELECT 1"}, query_input, "missing database/generation/mode")
    value_schema = {"$defs": data["$defs"], "$ref": "#/$defs/sql_value"}
    must_reject({"type": "integer", "value": 42}, value_schema, "lossy JSON-number integer")
    must_reject({"type": "null", "value": "null"}, value_schema, "SQL null confused with text")
    validate({"type": "json", "value": None}, value_schema)
    validate({"type": "blob", "value": ""}, value_schema)
    examples = re.findall(r"~~~json\s*\n(.*?)\n~~~", (DOCS / "query-protocols.md").read_text(encoding="utf-8"), re.DOTALL)
    require(len(examples) == 2, "Query request/result examples not found")
    request = json.loads(examples[0])
    request["database_id"] = "019a0000-0000-7000-8000-000000000002"
    validate(request, query_input)
    validate(json.loads(examples[1]), query_output)
    return len(operations)


def check_requirements() -> int:
    rows = read_json(CONTRACTS / "requirements.json")["requirements"]
    expected = {f"{area}-{n:03}" for area, (_, obligations) in REQUIREMENTS.items() for n in range(1, len(obligations)+1)}
    actual = [x["id"] for x in rows]
    require(len(actual) == len(set(actual)) and set(actual) == expected, "Requirement range mismatch")
    scope = (DOCS / "product-scope.md").read_text(encoding="utf-8")
    ranges = {area: (int(first), int(last)) for area, first, last in re.findall(r"\b([A-Z]+)-(\d+)\.\.(\d+)", scope)}
    for area, (_, obligations) in REQUIREMENTS.items():
        if area == "SCOPE":
            require(all(f"SCOPE-{n:03}" in scope for n in range(1, len(obligations)+1)), "Scope row mismatch")
        else:
            require(ranges.get(area) == (1, len(obligations)), f"Product range differs from records: {area}")
    for row in rows:
        require((DOCS / row["owner_document"]).exists(), f"Missing requirement owner: {row['id']}")
        require((DOCS / row["acceptance_document"]).exists(), f"Missing acceptance owner: {row['id']}")
        require(len(row["acceptance"]) > 70, f"Empty acceptance: {row['id']}")
    return len(rows)


def check_config() -> int:
    schema = read_json(CONTRACTS / "config.schema.json")
    config = read_json(DOCS / "examples" / "mira.config.json")
    check_schema(schema)
    validate(config, schema)
    require(config["resources"]["operator_database_count_limit"] is None, "Example imposes database-count cap")
    mutations = []
    for key in ("unknown_setting", "cloud", "cluster"):
        candidate = copy.deepcopy(config)
        candidate[key] = {}
        mutations.append((candidate, key))
    candidate = copy.deepcopy(config)
    candidate["resources"]["max_active_databases"] = 0
    mutations.append((candidate, "invalid active budget"))
    candidate = copy.deepcopy(config)
    del candidate["postgres"]
    mutations.append((candidate, "missing PG configuration"))
    candidate = copy.deepcopy(config)
    candidate["resources"]["operator_database_count_limit"] = "unlimited"
    mutations.append((candidate, "invalid count policy type"))
    for candidate, label in mutations:
        must_reject(candidate, schema, label)
    # Schema syntax is separate from runtime TLS/path/budget cross-field checks.
    return len(mutations)


def check_sql() -> int:
    sql = (CONTRACTS / "catalog.sql").read_text(encoding="utf-8")
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(sql)
        require(connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1, "Foreign keys disabled")
        require(connection.execute("PRAGMA foreign_key_check").fetchall() == [], "Invalid empty catalog FK state")
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        for (table,) in tables:
            # Resolve FK targets even when the catalog has no data rows.
            for fk in connection.execute(f'PRAGMA foreign_key_list("{table}")'):
                require(connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (fk[2],)).fetchone() is not None, f"Missing FK table: {table}->{fk[2]}")
        return len(tables)


def check_evidence() -> tuple[int, int, str]:
    data = read_json(CONTRACTS / "source-evidence.json")
    require(data["revision"] == REVISION, "Evidence revision mismatch")
    for record in data["records"]:
        require(REVISION in record["url"], "Unpinned local evidence URL")
        if SOURCE_ROOT is not None:
            path = SOURCE_ROOT / record["path"]
            require(hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest() == record["sha256"], f"Changed audited source: {path}")
            lines = path.read_text(encoding="utf-8").splitlines()
            require(re.search(record["pattern"], lines[record["line"] - 1]) is not None, f"Wrong evidence anchor: {path}")
    inventory = read_json(CONTRACTS / "upstream-capabilities.json")
    require(inventory["revision"] == REVISION, "Capability revision mismatch")
    if SOURCE_ROOT is not None:
        require(inventory["rows"] == extract_capabilities(), "Upstream inventory differs from source tables")
    require({r["dialect"] for r in inventory["rows"]} == {"sqlite", "postgres"}, "Missing dialect inventory")
    if SOURCE_ROOT is not None:
        git = subprocess.run(["git", "rev-parse", f"{REVISION}^{{commit}}"], cwd=SOURCE_ROOT, text=True, capture_output=True, check=True)
        require(git.stdout.strip() == REVISION, "Audited commit not available in source checkout")
    source_status = "passed against separate source checkout" if SOURCE_ROOT is not None else "skipped: source checkout unavailable; document structure checked only"
    return len(data["records"]), len(inventory["rows"]), source_status


def main() -> None:
    # Parse all JSON, including examples, with duplicate-key rejection.
    json_files = list(DOCS.rglob("*.json"))
    for path in json_files:
        read_json(path)
    documents, links = check_links()
    operations = check_operations()
    requirements = check_requirements()
    negatives = check_config()
    tables = check_sql()
    evidence, capabilities, source_status = check_evidence()
    words = sum(len(re.findall(r"\S+", p.read_text(encoding="utf-8"))) for p in DOCS.rglob("*.md") if p.name != "validation-report.md")
    print(json.dumps({"result": "passed", "markdown_documents": documents, "markdown_words_excluding_validation_report": words,
        "local_links": links, "json_files": len(json_files), "operations": operations,
        "requirements": requirements, "catalog_tables": tables,
        "configuration_rejection_cases": negatives, "source_evidence_records": evidence,
        "upstream_status_rows": capabilities, "source_verification": source_status, "sqlite_parser_version": sqlite3.sqlite_version,
        "limits": "Documentation checks only; schema keyword subset, independent SQLite syntax, no native/Go application tests"}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, sqlite3.Error, subprocess.CalledProcessError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
