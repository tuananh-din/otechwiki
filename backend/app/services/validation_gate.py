"""Validation gate: blocks unqualified documents from entering the search index.

Rules enforced:
1. No raw files → index
2. No web imports before cleaning
3. Required metadata must be present
4. doc_type must be in ALLOWED_DOC_TYPES
5. Structured JSON must pass schema validation
6. No duplicate source IDs
"""
import json
from dataclasses import dataclass, field
from pathlib import Path


ALLOWED_DOC_TYPES = frozenset({
    "product", "product_specs", "policy", "faq",
    "internal_note", "pricing", "compare", "error_code",
})

ALLOWED_LAYERS = frozenset({"raw", "cleaned", "structured", "indexed", "legacy"})
ALLOWED_STATUSES = frozenset({"legacy", "draft", "reviewed", "canonical"})

# Required metadata fields for indexing
REQUIRED_FOR_INDEX = {"doc_type", "canonical_status"}

# JSON schemas for structured records (lightweight validation)
STRUCTURED_SCHEMAS = {
    "product_specs": {
        "required": ["product_code", "product_name", "specs"],
        "specs_fields": ["category", "key", "value"],
    },
    "faq_pairs": {
        "required": ["product_code", "question", "answer"],
    },
    "pricing": {
        "required": ["product_code", "product_name", "price", "currency"],
    },
    "compare": {
        "required": ["products", "criteria"],
    },
    "policies": {
        "required": ["policy_type", "title", "content"],
    },
    "error_codes": {
        "required": ["code", "description", "solution"],
    },
}


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> "ValidationResult":
        self.valid = False
        self.errors.append(msg)
        return self

    def warn(self, msg: str) -> "ValidationResult":
        self.warnings.append(msg)
        return self


def validate_for_indexing(
    knowledge_layer: str | None,
    canonical_status: str | None,
    doc_type: str | None,
    source_type: str | None = None,
    knowledge_path: str | None = None,
) -> ValidationResult:
    """Check if a document qualifies for indexing."""
    result = ValidationResult()

    # Rule 1: No raw files
    if knowledge_layer == "raw":
        result.fail("Raw files cannot be indexed. Must be cleaned or structured first.")

    # Rule 2: Layer must be valid
    if knowledge_layer and knowledge_layer not in ALLOWED_LAYERS:
        result.fail(f"Unknown knowledge_layer: '{knowledge_layer}'. Allowed: {ALLOWED_LAYERS}")

    # Rule 3: Web imports must be cleaned first
    if source_type == "web" and knowledge_layer not in ("cleaned", "structured", "indexed", "legacy"):
        result.fail("Web imports must be cleaned before indexing.")

    # Rule 4: Required metadata
    if not doc_type and knowledge_layer != "legacy":
        result.fail("doc_type is required for non-legacy documents.")

    if not canonical_status and knowledge_layer != "legacy":
        result.fail("canonical_status is required for non-legacy documents.")

    # Rule 5: doc_type must be known
    if doc_type and doc_type not in ALLOWED_DOC_TYPES:
        result.fail(f"Unknown doc_type: '{doc_type}'. Allowed: {ALLOWED_DOC_TYPES}")

    # Rule 6: canonical_status must be valid
    if canonical_status and canonical_status not in ALLOWED_STATUSES:
        result.fail(f"Unknown canonical_status: '{canonical_status}'. Allowed: {ALLOWED_STATUSES}")

    # Legacy documents always pass (backward compat)
    if knowledge_layer == "legacy":
        result.valid = True
        result.errors.clear()

    return result


def validate_structured_json(json_path: str | Path, doc_type: str) -> ValidationResult:
    """Validate structured JSON file against its schema."""
    result = ValidationResult()
    path = Path(json_path)

    if not path.exists():
        return result.fail(f"File not found: {path}")

    if not path.suffix == ".json":
        return result.fail(f"Structured records must be JSON. Got: {path.suffix}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return result.fail(f"Invalid JSON: {e}")

    # Check schema if doc_type has one
    schema = STRUCTURED_SCHEMAS.get(doc_type)
    if not schema:
        result.warn(f"No schema defined for doc_type '{doc_type}'. Skipping schema check.")
        return result

    # Handle both single records and arrays
    records = data if isinstance(data, list) else [data]

    for i, record in enumerate(records):
        if not isinstance(record, dict):
            result.fail(f"Record [{i}]: expected object, got {type(record).__name__}")
            continue

        for field_name in schema["required"]:
            if field_name not in record or record[field_name] is None:
                result.fail(f"Record [{i}]: missing required field '{field_name}'")

    return result


def check_duplicate_source(
    source_url: str | None,
    source_hash: str | None,
    registry_path: str | Path,
) -> ValidationResult:
    """Check if source already registered (dedup)."""
    result = ValidationResult()
    registry = Path(registry_path)

    if not registry.exists():
        return result  # No registry yet, pass

    try:
        with open(registry, "r", encoding="utf-8") as f:
            reg_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return result

    sources = reg_data.get("sources", [])

    if source_url:
        for s in sources:
            if s.get("url") == source_url:
                result.fail(f"Duplicate source URL: {source_url} (existing ID: {s.get('id')})")
                return result

    if source_hash:
        for s in sources:
            if s.get("hash") == source_hash:
                result.warn(f"Content hash match with existing source ID: {s.get('id')}. Possible duplicate.")

    return result
