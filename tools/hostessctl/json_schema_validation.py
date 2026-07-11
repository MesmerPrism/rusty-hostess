"""Small dependency-free validator for checked-in Hostess JSON schemas.

The Hostess CLI intentionally has no third-party Python runtime dependency.
This validator implements the JSON Schema 2020-12 keywords used by the
checked-in project-runner and schema-ownership schemas. Unsupported keywords
fail closed so adding a schema feature cannot silently weaken validation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SUPPORTED_SCHEMA_KEYS = {
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "title",
    "description",
    "type",
    "const",
    "enum",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
    "minimum",
    "maximum",
}


class CheckedSchemaError(ValueError):
    """A document or checked-in schema failed validation."""


def load_and_validate_checked_schema(
    document: Any,
    schema_path: Path,
    *,
    label: str,
) -> None:
    """Validate *document* against one checked-in schema file."""

    if not schema_path.is_file():
        raise CheckedSchemaError(f"{label}: checked-in schema is missing: {schema_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise CheckedSchemaError(f"{label}: checked-in schema must be one JSON object")
    _validate_schema_keywords(schema, label=f"{schema_path.name} schema")
    _validate(document, schema, schema, path="$", label=label)


def _validate_schema_keywords(value: Any, *, label: str) -> None:
    if not isinstance(value, dict):
        raise CheckedSchemaError(f"{label}: every schema node must be an object")
    unknown = sorted(set(value) - SUPPORTED_SCHEMA_KEYS)
    if unknown:
        raise CheckedSchemaError(
            f"{label}: unsupported JSON Schema keywords: {', '.join(unknown)}"
        )
    for container_key in ("$defs", "properties"):
        container = value.get(container_key, {})
        if not isinstance(container, dict):
            raise CheckedSchemaError(f"{label}: {container_key} must be an object")
        for child in container.values():
            _validate_schema_keywords(child, label=label)
    for child_key in ("items", "additionalProperties"):
        child = value.get(child_key)
        if isinstance(child, dict):
            _validate_schema_keywords(child, label=label)


def _validate(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    *,
    path: str,
    label: str,
) -> None:
    if "$ref" in schema:
        resolved = _resolve_local_ref(root_schema, str(schema["$ref"]), label=label)
        _validate(value, resolved, root_schema, path=path, label=label)
        return

    if "const" in schema and value != schema["const"]:
        raise CheckedSchemaError(
            f"{label}: {path} must equal {schema['const']!r}, observed {value!r}"
        )
    if "enum" in schema and value not in schema["enum"]:
        raise CheckedSchemaError(
            f"{label}: {path} must be one of {schema['enum']!r}, observed {value!r}"
        )

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(value, expected_type):
        raise CheckedSchemaError(
            f"{label}: {path} must have JSON type {expected_type!r}"
        )

    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise CheckedSchemaError(
                f"{label}: {path} is missing required fields: {', '.join(missing)}"
            )
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, child in value.items():
            child_schema = properties.get(key)
            if child_schema is None:
                if additional is False:
                    raise CheckedSchemaError(f"{label}: {path}.{key} is not allowed")
                if isinstance(additional, dict):
                    child_schema = additional
            if isinstance(child_schema, dict):
                _validate(
                    child,
                    child_schema,
                    root_schema,
                    path=f"{path}.{key}",
                    label=label,
                )

    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            raise CheckedSchemaError(f"{label}: {path} has too few items")
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            raise CheckedSchemaError(f"{label}: {path} has too many items")
        if schema.get("uniqueItems") is True:
            encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(encoded) != len(set(encoded)):
                raise CheckedSchemaError(f"{label}: {path} items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, child in enumerate(value):
                _validate(
                    child,
                    item_schema,
                    root_schema,
                    path=f"{path}[{index}]",
                    label=label,
                )

    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            raise CheckedSchemaError(f"{label}: {path} is shorter than minLength")
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            raise CheckedSchemaError(f"{label}: {path} is longer than maxLength")
        if "pattern" in schema and re.search(str(schema["pattern"]), value) is None:
            raise CheckedSchemaError(
                f"{label}: {path} does not match pattern {schema['pattern']!r}"
            )

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise CheckedSchemaError(f"{label}: {path} is below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise CheckedSchemaError(f"{label}: {path} is above maximum")


def _resolve_local_ref(
    root_schema: dict[str, Any],
    ref: str,
    *,
    label: str,
) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise CheckedSchemaError(f"{label}: only local JSON Schema refs are supported: {ref}")
    current: Any = root_schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise CheckedSchemaError(f"{label}: unresolved local JSON Schema ref: {ref}")
        current = current[part]
    if not isinstance(current, dict):
        raise CheckedSchemaError(f"{label}: JSON Schema ref does not resolve to an object: {ref}")
    return current


def _matches_type(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_matches_type(value, candidate) for candidate in expected)
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(str(expected), False)


__all__ = ["CheckedSchemaError", "load_and_validate_checked_schema"]
