import json
from pathlib import Path

specs_dir = Path('/app/knowledge/structured/product_specs')
promoted = 0
for f in sorted(specs_dir.glob('*.json')):
    try:
        data = json.loads(f.read_text())
        if data.get('extraction_status') == 'draft':
            data['extraction_status'] = 'canonical'
            data['promoted_at'] = '2026-03-12T01:50:00+00:00'
            data['reviewed_by'] = 'admin'
            data['last_reviewed_at'] = '2026-03-12T01:50:00+00:00'
            data['needs_review'] = False
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            promoted += 1
            print(f'  promoted: {f.name}')
        else:
            print(f'  skip: {f.name} ({data.get("extraction_status")})')
    except Exception as e:
        print(f'  error: {f.name}: {e}')
print(f'\nTotal promoted: {promoted}')
