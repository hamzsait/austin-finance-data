"""Load Fuentes AIPAC/pro-Israel/Jewish civic findings."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # ADAM LOEWY - Loewy Law Firm, Austin 78731 (Legal).
    # Fuentes batch 1 line 86 "Loewy, Adam / attorney / Legal / Austin 78731" and
    # batch 2 line 135 "Loewy, Adam / attorney / Legal / Austin 78731" = same donor as
    # Velasquez research. Firm bio says "keen interest in pro-Israel politics and is
    # involved with AIPAC"; 2022 Shalom Austin Annual Campaign Co-Chair; Joe Krassner
    # Campaign Leadership Award; Prime Ministers Council ($100K+) member.
    ('Loewy, Adam', 'American Israel Public Affairs Committee (AIPAC)',
     'Public supporter / donor (self-stated pro-Israel political interest)',
     'pro_israel', 'https://personalinjurylawyersaustintx.com/leadership/',
     'Loewy Law Firm leadership bio states AIPAC is among organizations the Loewys actively support; Texas Hillel alumni spotlight says Adam has "keen interest in pro-Israel politics and is involved with AIPAC". Disambiguation: Fuentes Loewy, Adam / attorney / Austin 78731 = Adam Jacob Loewy, Loewy Law Firm P.C.'),
    ('Loewy, Adam', 'Shalom Austin (Jewish Federation of Greater Austin)',
     '2022 Annual Campaign Co-Chair; Joe Krassner Campaign Leadership Award recipient',
     'jewish_civic', 'https://shalomaustin.org/2023/01/13/2022-annual-campaign/',
     'Shalom Austin CEO letter confirms Adam and brother Phil served as 2022 Campaign Co-Chairs. Adam received the Joe Krassner Campaign Leadership Award from Jewish Federation of Austin.'),
    ('Loewy, Adam', 'Jewish Federations of North America - Prime Ministers Council',
     'Member ($100,000+ giving society)',
     'jewish_civic', 'https://ejewishphilanthropy.com/when-disaster-strikes-jewish-philanthropy-in-action-central-texas-flood/',
     'Adam and Phil Loewy joined 150 members of Jewish Federations Prime Ministers Council (national top-giving society).'),

    # PHIL LOEWY (Philippa Loewy) - Loewy Law Firm, Austin 78731 (Legal).
    # Fuentes batch 1 line 35 "Loewy, Phil / firm hr law loewy / Legal / Austin 78731"
    # and batch 2 line 118 same. Public records show Philippa (female, Adam's
    # sister-in-law via family firm) is the Shalom Austin board chair.
    ('Loewy, Phil', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Board Chair; Executive Committee; Philanthropy Committee Chair',
     'jewish_civic', 'https://shalomaustin.org/leadership/',
     'Phil (Philippa) Loewy of Loewy Law Firm serves on the Shalom Austin Board and Executive Committee as Philanthropy Committee Chair, and is confirmed as Board Chair. Disambiguation: Fuentes donor Loewy, Phil / law firm loewy hr / Austin 78731 matches firm address and family.'),
    ('Loewy, Phil', 'American Israel Public Affairs Committee (AIPAC)',
     'Public supporter / donor (family-stated)',
     'pro_israel', 'https://personalinjurylawyersaustintx.com/leadership/',
     'Loewy Law Firm bio lists AIPAC among organizations Phil and Adam actively support.'),
    ('Loewy, Phil', 'Jewish Federations of North America - Prime Ministers Council',
     'Member ($100,000+ giving society)',
     'jewish_civic', 'https://ejewishphilanthropy.com/when-disaster-strikes-jewish-philanthropy-in-action-central-texas-flood/',
     'Phil and Adam Loewy joined Jewish Federations Prime Ministers Council.'),

    # BOBBY / ROBERT EPSTEIN - Prophet Capital Management ("PCM"), COTA Chairman.
    # Fuentes batch 1 line 54 "Epstein, Robert / employed not / Technology / Austin 78791"
    # and batch 1 line 147 "Epstein, Aubrey / employed not / Austin 78791" (78791 is
    # a typo for Austin; matches 78701 downtown Bobby Epstein residence).
    ('Epstein, Robert', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($50,000-$99,999), 2022-2023 Honor Roll (as Aubrey and Bobby Epstein)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Aubrey and Bobby Epstein listed in King David Society tier on 2022-2023 Shalom Austin Honor Roll. Bobby Epstein founded Prophet Capital Management in 1995 (also Chairman/co-founder Circuit of the Americas). Same donor as Velasquez Epstein, Robert at 78701 (78791 is typo).'),
    ('Epstein, Robert', 'Texas Hillel', 'Donor (listed as Aubrey and Robert Epstein)',
     'jewish_civic', 'https://texashillel.org/donors/',
     'Listed on Texas Hillel donor page as Aubrey and Robert Epstein.'),

    # AUBREY EPSTEIN - Austin 78791 (Fuentes batch 1 line 147), wife of Bobby Epstein.
    ('Epstein, Aubrey', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($50,000-$99,999), 2022-2023 Honor Roll (as Aubrey and Bobby Epstein)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Aubrey and Bobby Epstein listed in King David Society tier on 2022-2023 Shalom Austin Honor Roll.'),
    ('Epstein, Aubrey', 'Texas Hillel', 'Donor (listed as Aubrey and Robert Epstein)',
     'jewish_civic', 'https://texashillel.org/donors/',
     'Listed on Texas Hillel donor page as Aubrey and Robert Epstein.'),

    # BUCK CODY - Managing Principal, Endeavor Real Estate Group, Austin 78703.
    # Fuentes batch 2 line 49 "Cody, Buck / endeavor estate investor real / Austin 78703".
    ('Cody, Buck', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($5,000-$9,999 tier), 2022-2023 Honor Roll (as Madeleine and Buck Cody)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Madeleine and Buck Cody on 2022-2023 Shalom Austin Honor Roll. Managing Principal at Endeavor Real Estate Group; 78703 Austin residence consistent.'),

    # MADELEINE CODY - Austin 78703 (Healthcare/homemaker), wife of Buck Cody.
    # Fuentes batch 1 line 79 "Cody, Madeleine / employed not / Healthcare / Austin 78703".
    ('Cody, Madeleine', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($5,000-$9,999 tier), 2022-2023 Honor Roll',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Madeleine and Buck Cody on 2022-2023 Shalom Austin Honor Roll.'),

    # DAVID WOLFF - Partner at Metcalfe Wolff Stuart & Williams, LLP (MWSW), Austin 78703.
    # Fuentes batch 1 line 106 "Wolff, David / attorney mwsw / Austin 78703".
    ('Wolff, David', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $10,000-$17,999 tier (2022-2023 Honor Roll, as Leslie and David Wolff)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Leslie and David Wolff at $10K-$17,999 tier on 2022-2023 Shalom Austin Honor Roll. David A. Wolff is a partner at Metcalfe Wolff Stuart & Williams (mwswtexas.com); Austin 78703 address consistent.'),

    # LESLIE WOLFF - Austin 78703, wife of David Wolff.
    # Fuentes batch 1 line 85 "Wolff, Leslie / unemployed / Real Estate / Austin 78703".
    ('Wolff, Leslie', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $10,000-$17,999 tier (2022-2023 Honor Roll, as Leslie and David Wolff)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as Leslie and David Wolff at $10K-$17,999 tier on 2022-2023 Shalom Austin Honor Roll.'),

    # MARC WINKELMAN - Chairman/CEO Calendar Club / Calendar Holdings / Go! Retail Group, Austin 78744.
    # Fuentes batch 2 line 8 "Winkelman, Marc / calendar executive services / Retail / Austin 78744".
    # Calendar Holdings is headquartered in Austin; Marc Winkelman is a major Jewish
    # civic figure - Secretary of National Jewish Democratic Council; Secretary of
    # Elie Wiesel Foundation for Humanity; Shalom Austin King David Society donor.
    ('Winkelman, Marc', 'National Jewish Democratic Council (NJDC)', 'Secretary',
     'liberal_zionist', 'https://texasbookfestival.org/directory/board-advisor/marc-winkelman/',
     'Texas Book Festival board bio explicitly identifies Marc Winkelman as "secretary of the National Jewish Democratic Council". NJDC is a Democratic-aligned Jewish pro-Israel political organization. Disambiguation: Fuentes Winkelman, Marc / calendar executive services / Austin 78744 = Marc Winkelman, CEO Calendar Club / Calendar Holdings (Austin HQ).'),
    ('Winkelman, Marc', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($25,000-$35,999 tier), 2022-2023 Honor Roll (as Suzanne z"l and Marc Winkelman)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Suzanne z\"l and Marc Winkelman" in King David Society tier ($25K-$35,999) on 2022-2023 Shalom Austin Honor Roll.'),
    ('Winkelman, Marc', 'Elie Wiesel Foundation for Humanity', 'Secretary',
     'jewish_civic', 'https://texasbookfestival.org/directory/board-advisor/marc-winkelman/',
     'Texas Book Festival board bio identifies Marc Winkelman as secretary of The Elie Wiesel Foundation for Humanity.'),

    # SANDY DOCHEN - retired IBM, Austin 78731.
    # Fuentes batch 3 line 118 "Dochen, Sandy / retired / Technology / Austin 78731".
    # Former Chair (Past President) of the Jewish Federation of Austin; JFNA Board of
    # Trustees member; long-time Shalom Austin leader; Joseph Krassner Campaign
    # Leadership Award recipient; King David Society donor.
    ('Dochen, Sandy', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Past President / Past Chair (Past Presidents Council); Audit Committee Chair',
     'jewish_civic', 'https://fliphtml5.com/iylbt/ermq/Shalom_Austin_2020-21_Honor_Roll/',
     'Sandy Dochen has chaired the Jewish Federation of Austin and is listed in the Past Presidents Council in 2022-2023 Shalom Austin leadership. He served as Chair of the Audit Committee in the 2020-2021 leadership structure. Disambiguation: Fuentes Dochen, Sandy / retired / Technology / Austin 78731 = Sandy Dochen, retired from IBM regional corporate social responsibility role in 2019.'),
    ('Dochen, Sandy', 'Jewish Federations of North America (JFNA)', 'Board of Trustees member',
     'jewish_civic', 'https://www.linkedin.com/in/sandydochen',
     'Sandy Dochen has served on the JFNA Board of Trustees (national umbrella of Jewish Federations).'),
    ('Dochen, Sandy', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($25,000-$35,999 tier), 2022-2023 Honor Roll (as Carol and Sandy Dochen)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Carol and Sandy Dochen" in King David Society tier ($25K-$35,999) on 2022-2023 Shalom Austin Honor Roll. Joseph Krassner Campaign Leadership Award recipient.'),

    # DARYL KUNIK - Founder / Principal, TOPO (formerly Central Austin Management Group),
    # Austin 78704. Fuentes batch 1 line 66 "Kunik, Daryl / founder principal topo /
    # Real Estate / Austin 78704". Son of Burt Kunik (JAMen founder).
    ('Kunik, Daryl', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Joshua Society donor ($10,000-$17,999 tier), 2022-2023 Honor Roll (as Dana and Daryl Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Dana and Daryl Kunik" in Joshua Society tier ($10K-$17,999) on 2022-2023 Shalom Austin Honor Roll. Daryl is founder/principal of TOPO (commercial real estate developer) and son of Burt Kunik (late JAMen Forum founder). Disambiguation: Fuentes Kunik, Daryl / founder principal topo / Austin 78704 unambiguous.'),

    # SANDY GOTTESMAN - former Trammell Crow; founder The Gottesman Company /
    # Live Oak-Gottesman merger; Austin 78703. Fuentes batch 1 line 133 "Gottesman,
    # Sandy / estate real / Real Estate / Austin 78703".
    ('Gottesman, Sandy', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($36,000-$49,999 tier), 2022-2023 Honor Roll (as Lisa and Sandy Gottesman)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Lisa and Sandy Gottesman" in King David Society tier ($36K-$49,999) on 2022-2023 Shalom Austin Honor Roll. Sandy Gottesman founded The Gottesman Company (Austin commercial real estate; later merged into Live Oak-Gottesman). "Sandy Gottesman Fund" is listed among Shalom Austin Jewish Foundation fundholders. Disambiguation: Austin 78703 real estate matches (distinct from deceased NY billionaire David "Sandy" Gottesman of First Manhattan).'),

    # LISA GOTTESMAN - Austin 78703, wife of Sandy Gottesman.
    # Fuentes batch 2 line 50 "Gottesman, Lisa / estate real / Austin 78703".
    ('Gottesman, Lisa', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'King David Society donor ($36,000-$49,999 tier), 2022-2023 Honor Roll (as Lisa and Sandy Gottesman)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Lisa and Sandy Gottesman" in King David Society tier ($36K-$49,999) on 2022-2023 Shalom Austin Honor Roll.'),

    # IRA MITZNER - President/CEO RIDA Development Corporation, Houston 77010.
    # Fuentes batch 1 line 51 "Mitzner, Ira / development estate real rida / Houston 77010".
    # MAJOR find: State of Israel Bonds board of directors; Chairman Yeshiva University
    # Board; American Society for Yad Vashem executive board; Texas Holocaust, Genocide,
    # and Antisemitism Advisory Commission (appointed by Gov. Abbott).
    ('Mitzner, Ira', 'State of Israel Bonds', 'Board of Directors',
     'jewish_civic', 'https://gov.texas.gov/news/post/governor-abbott-appoints-mitzner-to-texas-holocaust-genocide-and-antisemitism-advisory-commission',
     'Texas Governor press release and RIDA Development leadership page confirm Ira Mitzner (President/CEO RIDA Development, Houston) serves on board of directors of State of Israel Bonds. Israel Bonds leadership is a verified pro-Israel / Jewish civic role. Disambiguation: Fuentes Mitzner, Ira / rida real estate / Houston 77010 is unambiguous.'),
    ('Mitzner, Ira', 'American Society for Yad Vashem', 'Executive Board',
     'jewish_civic', 'https://ridadev.com/leadership/',
     'RIDA Development leadership page confirms Ira Mitzner serves on the executive board of the American Society for Yad Vashem.'),
    ('Mitzner, Ira', 'Yeshiva University', 'Chairman of the Board',
     'jewish_civic', 'https://ridadev.com/leadership/',
     'RIDA Development leadership page confirms Ira Mitzner is Chairman of the Board of Yeshiva University.'),
    ('Mitzner, Ira', 'Texas Holocaust, Genocide, and Antisemitism Advisory Commission',
     'Commissioner (appointed by Governor Abbott)',
     'jewish_civic', 'https://gov.texas.gov/news/post/governor-abbott-appoints-mitzner-to-texas-holocaust-genocide-and-antisemitism-advisory-commission',
     'Governor Abbott press release announcing appointment of Ira Mitzner (RIDA Development CEO, son of Holocaust survivor) to the Commission.'),

    # MICHAEL P. MITZNER - RIDA Development, Houston 77010, Ira Mitzner family member.
    # Fuentes batch 2 line 37 "Mitzner, Michael P. / estate real rida / Houston 77010".
    # Same RIDA Development family ownership as Ira; same address; Mitzner family
    # is major Jewish philanthropic family (American Society for Yad Vashem, Yeshiva U).
    ('Mitzner, Michael P.', 'RIDA Development Corporation (Mitzner family)',
     'Family member / executive at firm with board-level Israel Bonds / Yad Vashem / Yeshiva University leadership',
     'jewish_civic', 'https://ridadev.com/leadership/',
     'RIDA Development is the Mitzner family firm founded 1975 by David Mitzner (Holocaust survivor). Ira Mitzner (CEO) sits on State of Israel Bonds board, American Society for Yad Vashem executive board, and chairs Yeshiva University. Michael P. Mitzner shares same RIDA Houston 77010 address and family ownership. Disambiguation: Fuentes Mitzner, Michael P. / rida real estate / Houston 77010 matches RIDA family firm.'),

    # J. DAVID HELLER - President, CEO, Co-Founder The NRP Group, Boca Raton FL.
    # Fuentes batch 2 line 74 "Heller, Jay David / ceo group nrp president / Real Estate
    # / Boca Raton, FL, 33432". MAJOR find: National Campaign Chair of Jewish
    # Federations of North America (JFNA); former Board Chairman Jewish Federation
    # of Cleveland; board Jewish Agency for Israel; board American Jewish Joint
    # Distribution Committee.
    ('Heller, Jay David', 'Jewish Federations of North America (JFNA)',
     'National Campaign Chair',
     'jewish_civic', 'https://www.jewishfederations.org/blog/all/j-david-heller-confirmed-as-national-campaign-chair-of-jewish-federations',
     'JFNA official blog announcing J. David Heller as National Campaign Chair (two-year term). JFNA is the national umbrella of 146 Jewish Federations raising $3 billion annually. Disambiguation: Fuentes Heller, Jay David / ceo group nrp / Boca Raton 33432 = J. David Heller, CEO The NRP Group (lives Cleveland and Boca Raton).'),
    ('Heller, Jay David', 'Jewish Federation of Cleveland',
     'Former Board Chairman (2019-2022 term)',
     'jewish_civic', 'https://www.jewishcleveland.org/news/blog/j_david_heller_named_jfna_national_campaign_chair/',
     'Jewish Federation of Cleveland announcement confirms J. David Heller served as Board Chairman for 2019-2022 term.'),
    ('Heller, Jay David', 'Jewish Agency for Israel', 'Board of Directors',
     'jewish_civic', 'https://nrpgroup.com/about-us/leadership/j-david-heller',
     'NRP Group leadership bio confirms J. David Heller serves on boards of Jewish Agency for Israel and American Jewish Joint Distribution Committee (Israel-focused Jewish global institutions).'),
    ('Heller, Jay David', 'American Jewish Joint Distribution Committee (JDC)',
     'Board of Directors',
     'jewish_civic', 'https://nrpgroup.com/about-us/leadership/j-david-heller',
     'NRP Group leadership bio confirms J. David Heller serves on JDC board (global Jewish humanitarian organization with major Israel operations).'),
]

added = 0
for row in new:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} AIPAC/pro-Israel/Jewish civic Fuentes findings')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations: {cur.fetchone()[0]}')
c.close()
