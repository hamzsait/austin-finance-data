"""Load Velasquez AIPAC/pro-Israel/Jewish civic findings."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # ADAM LOEWY — Loewy Law Firm, Austin 78731 (Legal).
    # Multiple independent verified public sources: publicly states support of AIPAC
    # ("The Loewys actively support... and AIPAC"); 2022 Shalom Austin Annual Campaign Co-Chair;
    # Joe Krassner Campaign Leadership Award recipient from Jewish Federation of Austin;
    # Prime Minister's Council ($100K+ giving society of Jewish Federations of North America)
    # via $100,000 gift with brother Phil; Texas Hillel alumni spotlight / donor.
    ('Loewy, Adam', 'American Israel Public Affairs Committee (AIPAC)', 'Public supporter / donor (self-stated pro-Israel political interest)',
     'pro_israel', 'https://personalinjurylawyersaustintx.com/leadership/',
     'Loewy Law Firm leadership bio and Texas Hillel alumni spotlight both state AIPAC is among organizations the Loewys actively support. Adam has "keen interest in pro-Israel politics and is involved with AIPAC." Disambiguation: Velasquez batch Loewy, Adam / law loewy / Austin 78731 = Adam Jacob Loewy, Loewy Law Firm P.C.'),
    ('Loewy, Adam', 'Shalom Austin (Jewish Federation of Greater Austin)', '2022 Annual Campaign Co-Chair; Joe Krassner Campaign Leadership Award recipient',
     'jewish_civic', 'https://shalomaustin.org/2023/01/13/2022-annual-campaign/',
     'Shalom Austin CEO letter and Loewy Law Firm bio confirm Adam and brother Phil served as 2022 Campaign Co-Chairs. Adam received the Joe Krassner Campaign Leadership Award from Jewish Federation of Austin.'),
    ('Loewy, Adam', 'Jewish Federations of North America - Prime Ministers Council',
     'Member ($100,000+ giving society)',
     'jewish_civic', 'https://ejewishphilanthropy.com/when-disaster-strikes-jewish-philanthropy-in-action-central-texas-flood/',
     'Adam and Phil Loewy joined 150 members of Jewish Federations Prime Ministers Council (national top-giving society).'),

    # PHIL LOEWY (Philippa Loewy) — Loewy Law Firm, Austin 78731 (Legal).
    # Adam's sister-in-law (per LinkedIn Philippa R Loewy, Loewy Law Firm P.C.).
    # NOTE: Velasquez file lists donor as "Loewy, Phil" but public records show
    # Philippa (female) is the Shalom Austin board chair. Same family / same firm.
    ('Loewy, Phil', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Board Chair; Executive Committee; Philanthropy Committee Chair',
     'jewish_civic', 'https://shalomaustin.org/leadership/',
     'Phil (Philippa) Loewy of Loewy Law Firm serves on the Shalom Austin Board and Executive Committee as Philanthropy Committee Chair, and is confirmed as Board Chair. Disambiguation: Velasquez donor Loewy, Phil / law firm loewy / Austin 78731 matches firm address and family.'),
    ('Loewy, Phil', 'American Israel Public Affairs Committee (AIPAC)',
     'Public supporter / donor (family-stated)',
     'pro_israel', 'https://personalinjurylawyersaustintx.com/leadership/',
     'Loewy Law Firm bio lists AIPAC among organizations Phil and Adam actively support.'),
    ('Loewy, Phil', 'Jewish Federations of North America - Prime Ministers Council',
     'Member ($100,000+ giving society)',
     'jewish_civic', 'https://ejewishphilanthropy.com/when-disaster-strikes-jewish-philanthropy-in-action-central-texas-flood/',
     'Phil and Adam Loewy joined Jewish Federations Prime Ministers Council.'),

    # BOBBY / ROBERT EPSTEIN — Prophet Capital Management ("PCM"), COTA Chairman,
    # Austin 78701 (Finance). Wife Aubrey Mayo Epstein.
    # Velasquez batch 1 line 75 = "Epstein, Robert / manager pcm / Finance / Austin 78701"
    # matches Robert "Bobby" Epstein (Prophet Capital founder / CIO / CEO).
    ('Epstein, Robert', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($50,000-$99,999), 2022-2023 Honor Roll (as Aubrey and Bobby Epstein)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Aubrey and Bobby Epstein listed in King David Society tier on 2022-2023 Shalom Austin Honor Roll. PCM = Prophet Capital Management, which Bobby Epstein founded in 1995 (also Chairman/co-founder Circuit of the Americas). Disambiguation: 78701 downtown address and "manager pcm" occupation unambiguous.'),
    ('Epstein, Robert', 'Texas Hillel', 'Donor (listed as Aubrey and Robert Epstein)',
     'jewish_civic', 'https://texashillel.org/donors/',
     'Listed on Texas Hillel donor page as Aubrey and Robert Epstein.'),

    # BURT KUNIK — retired endodontist/business executive, Austin 78731 (deceased Aug 2024).
    # Velasquez batch 2 = "Kunik, Burton / retired / Austin 78731". Founder and Chair of
    # the Shalom Austin Jewish Austin Men (JAMen) Dinner and Speakers Forum, which was
    # renamed in his honor posthumously as the "Burt Kunik JAMen Forum."
    ('Kunik, Burton', 'Shalom Austin - Jewish Austin Men (JAMen) Forum',
     'Founder and Chair (forum renamed "Burt Kunik JAMen Forum" in his honor)',
     'jewish_civic', 'https://shalomaustin.org/2025/02/25/jamen-jo25/',
     'Shalom Austin article explicitly identifies Burt Kunik as "visionary founder and chair" of JAMen, founded 2015 after Burt moved to Austin from Houston. Obituary in Austin American-Statesman (Aug 8 2024) confirms and notes family requested memorial donations to Shalom Austin (JAMen Forum) and ADL. Disambiguation: Velasquez Kunik, Burton / retired / Austin 78731 matches.'),
    ('Kunik, Burton', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $5,000-$9,999 tier (2022-2023 Honor Roll, listed as Mary and Burt Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Mary and Burt Kunik at $5K-$9,999 tier on 2022-2023 Shalom Austin Honor Roll.'),

    # MARY KUNIK — retired, Austin 78731, widow of Burt Kunik.
    # Velasquez batch 2 = "Kunik, Mary / retired / Austin 78731".
    ('Kunik, Mary', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $5,000-$9,999 tier (2022-2023 Honor Roll, listed as Mary and Burt Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Mary and Burt Kunik at $5K-$9,999 tier. Matriarch of Austin Kunik family; moved to Austin from Houston in 2014.'),

    # BUCK CODY — Managing Principal, Endeavor Real Estate Group, Austin 78703.
    # Velasquez batch 1 = "Cody, Buck / endeavor estate group investor real / Austin 78703".
    ('Cody, Buck', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($5,000-$9,999 tier), 2022-2023 Honor Roll (as Madeleine and Buck Cody)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Madeleine and Buck Cody on 2022-2023 Shalom Austin Honor Roll. Managing Principal at Endeavor Real Estate Group (confirmed via Bloomberg profile); 78703 Austin residence consistent.'),

    # MADELEINE CODY — Austin 78703 (Healthcare/homemaker), wife of Buck Cody.
    # Velasquez batch 2 = "Cody, Madeleine / homemaker / Healthcare / Austin 78703".
    ('Cody, Madeleine', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($5,000-$9,999 tier), 2022-2023 Honor Roll',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Madeleine and Buck Cody on 2022-2023 Shalom Austin Honor Roll.'),

    # DAVID WOLFF — Partner at Metcalfe Wolff Stuart & Williams, LLP (MWSW),
    # Austin 78703 (Legal/Consulting per batch 3). Wife Leslie Wolff.
    # Velasquez batch 3 = "Wolff, David / attorney mwsw / Austin 78703".
    ('Wolff, David', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $10,000-$17,999 tier (2022-2023 Honor Roll, as Leslie and David Wolff)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Leslie and David Wolff at $10K-$17,999 tier on 2022-2023 Shalom Austin Honor Roll. David A. Wolff is a partner at Metcalfe Wolff Stuart & Williams (mwswtexas.com); Austin 78703 address consistent.'),
]

added = 0
for row in new:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} AIPAC/pro-Israel/Jewish civic Velasquez findings')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations: {cur.fetchone()[0]}')
c.close()
