from pathlib import Path
text = Path('Makhzan/templates/base.html').read_text(encoding='utf-8').splitlines()
for idx,line in enumerate(text[:200],start=1):
    if 'purchases' in line or 'sales' in line:
        print(idx,line)
