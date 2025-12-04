from pathlib import Path
path = Path('app.py')
lines = path.read_text(encoding='utf-8').splitlines()
for i, line in enumerate(lines):
    if 'desc_idx = find_index' in line:
        lines.insert(i+1, "      notes_idx = find_index(['notes', 'ملاحظات', 'remarks', 'comments'])")
        break
else:
    raise SystemExit('desc_idx line not found')
path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
