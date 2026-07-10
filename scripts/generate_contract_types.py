from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "studio.schema.json"
OUTPUT = ROOT / "frontend" / "src" / "generated-contracts.ts"
HEADER = "// Generated from contracts/studio.schema.json. Do not edit by hand.\n\n"


def ts_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    if "anyOf" in schema:
        return " | ".join(ts_type(item) for item in schema["anyOf"])
    if "enum" in schema:
        return " | ".join(json.dumps(item, ensure_ascii=False) for item in schema["enum"])
    kind = schema.get("type")
    if kind == "string":
        return "string"
    if kind in {"number", "integer"}:
        return "number"
    if kind == "boolean":
        return "boolean"
    if kind == "null":
        return "null"
    if kind == "array":
        return f"Array<{ts_type(schema.get('items', {}))}>"
    if kind == "object":
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Record<string, {ts_type(additional)}>"
        return "Record<string, unknown>"
    return "unknown"


def render_definition(name: str, schema: dict[str, Any]) -> str:
    if schema.get("type") != "object" or not schema.get("properties"):
        return f"export type {name} = {ts_type(schema)};\n"
    required = set(schema.get("required", []))
    lines = [f"export interface {name} {{"]
    for field, field_schema in schema["properties"].items():
        optional = "" if field in required else "?"
        lines.append(f"  {field}{optional}: {ts_type(field_schema)};")
    lines.append("}\n")
    return "\n".join(lines)


def generate() -> str:
    document = json.loads(SCHEMA.read_text(encoding="utf-8"))
    return HEADER + "\n".join(render_definition(name, schema) for name, schema in document["$defs"].items())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = generate()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != generated:
            raise SystemExit("generated-contracts.ts is stale; run scripts/generate_contract_types.py")
        return 0
    OUTPUT.write_text(generated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
