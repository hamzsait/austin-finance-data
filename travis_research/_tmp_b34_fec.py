import sqlite3, json
c = sqlite3.connect(r'C:\Users\Hamza Sait\Electoral\austin-finance-data\austin_finance.db')
cur = c.cursor()
ids = [
 ("50b09485-55a2-4c17-b430-7442e629d390","Wehbe, Tareza"),
 ("4e79d2d3-0be8-470e-a072-c12a268eae5e","Ruf, Benjamin"),
 ("4e1553c3-299b-446e-8d00-28f5de7cbbf8","Clemons, Elizabeth Skipwith"),
 ("4c82a8bc-d7c0-458b-b1d3-096a23197349","Inabinet, Jennifer"),
 ("4ab5154d-b2d9-4f83-b573-0a45b3b8fa25","Chen, Xiao Ping"),
 ("483fabc1-a016-4b58-bd80-834b9df7d218","Kozmetsky, Greg"),
 ("4804b9ae-0579-4696-b936-495d4a933c8f","Holmes, Evelyn"),
 ("4b236579-ee66-41d1-bc73-32a029e2675a","Stripling, Sam"),
 ("48cc8489-1784-4c22-96a7-846d603f94e4","Solis, Pedro"),
 ("42a8bb60-de1d-4632-9641-788d3f128bc1","Qizilbash, Ambreen"),
]
cur.execute("select name from sqlite_master where type='table'")
print("TABLES:", [r[0] for r in cur.fetchall()])
for did, nm in ids:
    print("\n=== %s (%s)" % (nm, did))
    try:
        cur.execute("""select fec_name, fec_employer, fec_occupation, fec_city, fec_state, fec_zip,
                              committee_name, party, contribution_receipt_date, contribution_receipt_amount
                       from fec_contributions_raw where donor_id=? order by contribution_receipt_date""", (did,))
        rows = cur.fetchall()
        for r in rows[:40]:
            print("   ", r)
        print("   total rows:", len(rows))
    except Exception as e:
        print("   ERR", e)
c.close()
