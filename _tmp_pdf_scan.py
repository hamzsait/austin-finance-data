import sys, glob
import pypdf
path = glob.glob(r"C:\Users\Hamza Sait\.claude\projects\C--Users-Hamza-Sait-Electoral-austin-finance-data\4081f28d-caed-40e5-a955-0cb8125bc8d5\tool-results\*.pdf")
print(path)
for f in path:
    r = pypdf.PdfReader(f)
    print(f, "pages", len(r.pages))
    for i, p in enumerate(r.pages):
        t = p.extract_text() or ""
        for key in ("Baggs", "Slad", "Nassour"):
            if key in t:
                print("=== page", i, "key", key)
                print(t)
                break
