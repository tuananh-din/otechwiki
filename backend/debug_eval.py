"""Debug script: investigate all eval failures in one pass."""
import json
from pathlib import Path
from app.services.structured_lookup import (
    lookup_specs, lookup_pricing, lookup_faq,
    _find_json_file, _slugify, get_structured_context
)

print("=" * 60)
print("DEBUG: Structured Data Investigation")
print("=" * 60)

# 1. Check file statuses
specs_dir = Path("/app/knowledge/structured/product_specs")
faq_dir = Path("/app/knowledge/structured/faq_pairs")

print("\n--- Product Specs Status ---")
for f in sorted(specs_dir.glob("*.json")):
    data = json.loads(f.read_text())
    status = data.get("extraction_status", "?")
    price = data.get("price", "no price")
    print(f"  {f.name}: status={status}, price={price}")

print("\n--- FAQ Pairs ---")
if faq_dir.exists():
    for f in sorted(faq_dir.glob("*.json")):
        data = json.loads(f.read_text())
        count = len(data) if isinstance(data, list) else 1
        print(f"  {f.name}: {count} entries")
else:
    print("  faq_pairs directory NOT FOUND!")

# 2. Test slugify
print("\n--- Slugify Tests ---")
tests = ["Roborock F25", "Roborock F25 Ace Pro", "Roborock H60 Ultra",
         "Dyad Pro Combo", "Roborock Dyad Pro Combo", "Flexi Pro",
         "Roborock Flexi Pro"]
for t in tests:
    print(f"  '{t}' -> '{_slugify(t)}'")

# 3. Test lookup_specs
print("\n--- Lookup Specs Tests ---")
for name in ["Roborock F25", "Roborock F25 Ace Pro", "Roborock H60 Ultra",
             "Dyad Pro Combo", "Roborock Dyad Pro Combo",
             "Flexi Pro", "Roborock Flexi Pro"]:
    result = lookup_specs(name)
    if result:
        print(f"  '{name}' -> FOUND: {result.get('product_name')} (status={result.get('extraction_status')})")
    else:
        print(f"  '{name}' -> NOT FOUND")

# 4. Test lookup_faq
print("\n--- Lookup FAQ Tests ---")
for name in ["Dyad Pro Combo", "Roborock Dyad Pro Combo", "Qrevo Curv"]:
    result = lookup_faq(name)
    if result:
        print(f"  '{name}' -> FOUND: {len(result)} entries")
    else:
        print(f"  '{name}' -> NOT FOUND")

# 5. Test get_structured_context (the main function used by RAG)
print("\n--- get_structured_context Tests ---")
test_cases = [
    ("Roborock F25", "price_lookup"),
    ("Roborock F25 Ace Pro", "price_lookup"),
    ("Roborock H60 Ultra", "specifications"),
    ("Dyad Pro Combo", "how_to"),
    ("Roborock Flexi Pro", "price_lookup"),
]
for name, intent in test_cases:
    ctx = get_structured_context(name, intent)
    if ctx:
        print(f"  '{name}' + '{intent}' -> {len(ctx)} chars")
        # Print first 100 chars
        print(f"    Preview: {ctx[:100]}...")
    else:
        print(f"  '{name}' + '{intent}' -> NONE")

# 6. Check _find_json_file directly
print("\n--- _find_json_file Tests ---")
for cat, name in [("product_specs", "F25 Ace Pro"), ("product_specs", "H60 Ultra"),
                   ("faq_pairs", "Dyad Pro Combo"), ("faq_pairs", "Qrevo Curv")]:
    result = _find_json_file(cat, name)
    print(f"  category='{cat}', name='{name}' -> {result}")

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)
