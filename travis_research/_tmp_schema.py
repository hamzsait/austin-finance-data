import sqlite3
c = sqlite3.connect(r"C:\Users\Hamza Sait\Electoral\austin-finance-data\austin_finance.db")
for (n,) in c.execute("select name from sqlite_master where type='table' order by name"):
    cols = [r[1] for r in c.execute(f"PRAGMA table_info('{n}')")]
    cnt = c.execute(f"select count(*) from '{n}'").fetchone()[0]
    print(f"{n} ({cnt}): {cols}")
