from pathlib import Path
import re
text = Path('Makhzan/app.py').read_text(encoding='utf-8')
match = re.search(r"@app\.route\('/reports/top-selling'[\s\S]+?return render_template\('reports/top_selling\.html'[\s\S]+?\n\n", text)
if match:
    segment = match.group(0)
    with open('segment.txt','wb') as f:
        f.write(segment.encode('utf-8'))
