import sqlite3
import os
path = os.path.join(os.getcwd(), 'makhzan.db')
conn = sqlite3.connect(path)
cur = conn.cursor()
def add(column_sql):
    try:
        cur.execute(column_sql)
    except sqlite3.OperationalError:
        pass
add("ALTER TABLE purchases ADD COLUMN amount_paid FLOAT NOT NULL DEFAULT 0")
add("ALTER TABLE purchases ADD COLUMN due_date DATE")
add("ALTER TABLE purchases ADD COLUMN notification_email TEXT")
add("ALTER TABLE purchases ADD COLUMN due_reminder_sent BOOLEAN NOT NULL DEFAULT 0")
add("ALTER TABLE sales ADD COLUMN amount_paid FLOAT NOT NULL DEFAULT 0")
add("ALTER TABLE sales ADD COLUMN due_date DATE")
add("ALTER TABLE sales ADD COLUMN notification_email TEXT")
add("ALTER TABLE sales ADD COLUMN due_reminder_sent BOOLEAN NOT NULL DEFAULT 0")
conn.commit()
conn.close()
