import sqlite3
c = sqlite3.connect('austin_finance.db')
cur = c.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(tables)
for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    print(t, [r[1] for r in cur.fetchall()])
