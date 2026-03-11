"""Manifest system: inventory, source registry, and import tracking for knowledge/ tree.

Manifests:
- inventory.json: listing of all files per layer
- source_registry.json: dedup tracking by URL/hash
- duplicate_report.json: near-dup detection
- migration_manifest.json: legacy → canonical tracking
"""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path


KNOWLEDGE_ROOT = Path("/app/knowledge")
MANIFEST_DIR = KNOWLEDGE_ROOT / "manifests"

LAYERS = ["raw", "cleaned", "structured", "chunks", "indexes"]
SUBLAYERS = {
    "raw": ["product", "policy", "faq", "internal", "web_import"],
    "cleaned": ["product", "policy", "faq", "internal"],
    "structured": ["product_specs", "faq_pairs", "policies", "pricing", "compare", "error_codes"],
    "chunks": ["product", "policy", "faq", "internal"],
    "indexes": ["vector", "keyword"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict | list:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_folder_structure() -> list[str]:
    """Create the full knowledge/ directory tree. Returns list of created dirs."""
    created = []
    dirs = [
        KNOWLEDGE_ROOT,
        MANIFEST_DIR,
        KNOWLEDGE_ROOT / "evals",
        KNOWLEDGE_ROOT / "logs",
    ]
    for layer, subs in SUBLAYERS.items():
        for sub in subs:
            dirs.append(KNOWLEDGE_ROOT / layer / sub)

    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))

    return created


def build_inventory() -> dict:
    """Scan knowledge/ tree and build inventory.json."""
    inventory = {
        "generated_at": _now_iso(),
        "layers": {},
        "total_files": 0,
    }

    for layer in LAYERS:
        layer_dir = KNOWLEDGE_ROOT / layer
        if not layer_dir.exists():
            inventory["layers"][layer] = {"total": 0, "categories": {}}
            continue

        layer_data = {"total": 0, "categories": {}}
        for sub in SUBLAYERS.get(layer, []):
            sub_dir = layer_dir / sub
            if not sub_dir.exists():
                layer_data["categories"][sub] = {"count": 0, "files": []}
                continue

            files = []
            for f in sub_dir.rglob("*"):
                if f.is_file():
                    files.append({
                        "name": f.name,
                        "path": str(f.relative_to(KNOWLEDGE_ROOT)),
                        "size_bytes": f.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            f.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    })

            layer_data["categories"][sub] = {"count": len(files), "files": files}
            layer_data["total"] += len(files)

        inventory["layers"][layer] = layer_data
        inventory["total_files"] += layer_data["total"]

    _write_json(MANIFEST_DIR / "inventory.json", inventory)
    return inventory


def register_source(
    doc_id: int,
    source_url: str | None = None,
    source_hash: str | None = None,
    doc_type: str | None = None,
    knowledge_layer: str | None = None,
) -> dict:
    """Register a source in source_registry.json for dedup tracking."""
    registry_path = MANIFEST_DIR / "source_registry.json"
    registry = _read_json(registry_path) or {"sources": [], "count": 0}

    entry = {
        "id": doc_id,
        "url": source_url,
        "hash": source_hash,
        "doc_type": doc_type,
        "knowledge_layer": knowledge_layer,
        "registered_at": _now_iso(),
    }

    # Update or append
    existing_idx = next(
        (i for i, s in enumerate(registry["sources"]) if s["id"] == doc_id),
        None,
    )
    if existing_idx is not None:
        registry["sources"][existing_idx] = entry
    else:
        registry["sources"].append(entry)

    registry["count"] = len(registry["sources"])
    _write_json(registry_path, registry)
    return entry


def log_migration(
    doc_id: int,
    from_layer: str,
    to_layer: str,
    status: str,
    notes: str = "",
) -> dict:
    """Log a migration step in migration_manifest.json."""
    manifest_path = MANIFEST_DIR / "migration_manifest.json"
    manifest = _read_json(manifest_path) or {"migrations": [], "count": 0}

    entry = {
        "doc_id": doc_id,
        "from_layer": from_layer,
        "to_layer": to_layer,
        "status": status,
        "notes": notes,
        "timestamp": _now_iso(),
    }

    manifest["migrations"].append(entry)
    manifest["count"] = len(manifest["migrations"])
    _write_json(manifest_path, manifest)
    return entry


def generate_duplicate_report(sources: list[dict]) -> dict:
    """Generate duplicate_report.json from source registry data."""
    report = {
        "generated_at": _now_iso(),
        "exact_duplicates": [],
        "hash_matches": [],
        "url_duplicates": [],
    }

    # Group by URL
    url_map: dict[str, list] = {}
    hash_map: dict[str, list] = {}

    for s in sources:
        if s.get("url"):
            url_map.setdefault(s["url"], []).append(s)
        if s.get("hash"):
            hash_map.setdefault(s["hash"], []).append(s)

    for url, entries in url_map.items():
        if len(entries) > 1:
            report["url_duplicates"].append({
                "url": url,
                "doc_ids": [e["id"] for e in entries],
                "count": len(entries),
            })

    for h, entries in hash_map.items():
        if len(entries) > 1:
            report["hash_matches"].append({
                "hash": h,
                "doc_ids": [e["id"] for e in entries],
                "count": len(entries),
            })

    report_path = MANIFEST_DIR / "duplicate_report.json"
    _write_json(report_path, report)
    return report


def file_hash(filepath: str | Path) -> str:
    """SHA-256 hash of file contents."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
