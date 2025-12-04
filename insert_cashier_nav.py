# -*- coding: utf-8 -*-
from pathlib import Path
path = Path('Makhzan/templates/base.html')
text = path.read_text(encoding='utf-8')
marker = "                        </li>\n                        {% if current_user.role == 'admin' %}"
pos_block = "                        </li>\n                        {% if current_user.role in ['cashier', 'admin'] %}\n                        <li class=\"nav-item\">\n                            <a class=\"nav-link {% if '/cashier' in request.path %}active{% endif %}\" href=\"{{ url_for('cashier_pos') }}\">\n                                <i class=\"fas fa-barcode\"></i>\n                                Cashier POS\n                            </a>\n                        </li>\n                        {% endif %}\n                        {% if current_user.role == 'admin' %}"
if marker not in text:
    raise SystemExit('marker missing for cashier link')
text = text.replace(marker, pos_block, 1)
marker2 = """                        <li class="nav-item">
                            <a class="nav-link {% if '/sales/due' in request.path %}active{% endif %}" href="{{ url_for('sales_due') }}">
                                <i class="fas fa-calendar-check"></i>
                                الديون المستحقة
                            </a>
                        </li>
                        {% endif %}"""

logs_block = """                        <li class="nav-item">
                            <a class="nav-link {% if '/sales/due' in request.path %}active{% endif %}" href="{{ url_for('sales_due') }}">
                                <i class="fas fa-calendar-check"></i>
                                الديون المستحقة
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link {% if '/cashier/logs' in request.path %}active{% endif %}" href="{{ url_for('cashier_logs') }}">
                                <i class="fas fa-list"></i>
                                Cashier Logs
                            </a>
                        </li>
                        {% endif %}"""

if marker2 not in text:
    raise SystemExit('marker missing for cashier logs link')
text = text.replace(marker2, logs_block, 1)
path.write_text(text, encoding='utf-8')
