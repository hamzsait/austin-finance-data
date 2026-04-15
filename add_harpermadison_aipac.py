"""Load Harper-Madison AIPAC/pro-Israel/Jewish civic findings."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # ==========================================================================
    # KUNIK FAMILY (multiple donors — Harper-Madison batches 1 & 2)
    # The Kunik family is led by Austin orthodontist Dr. Randall "Randy" Kunik
    # (Kunik Orthodontics); Burt Kunik (deceased Aug 2024) was founder and chair
    # of Shalom Austin's Jewish Austin Men (JAMen) Forum. Multiple Kuniks appear
    # on Shalom Austin Honor Rolls.
    # ==========================================================================

    # BURTON "BURT" KUNIK — retired, Austin 78746. Harper-Madison batch 1 line 126
    # ("Kunik, Burton / ceo compliance sharps / Austin 78746"). Note Velasquez
    # crawl already captured same person at 78731; same identity.
    ('Kunik, Burton', 'Shalom Austin - Jewish Austin Men (JAMen) Forum',
     'Founder and Chair (forum renamed "Burt Kunik JAMen Forum" posthumously)',
     'jewish_civic', 'https://shalomaustin.org/2025/02/25/jamen-jo25/',
     'Shalom Austin article identifies Burt Kunik as "visionary founder and chair" of JAMen, founded 2015 after moving to Austin from Houston. Obituary (Aug 8 2024) requested memorial donations to Shalom Austin JAMen Forum. Harper-Madison batch 1 "Kunik, Burton / ceo compliance sharps / Austin 78746" matches same Burt Kunik.'),
    ('Kunik, Burton', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $1,000-$1,799 tier (2022-2023 Honor Roll as Mary and Burt Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Mary and Burt Kunik" in the 2022-2023 Shalom Austin Honor Roll at $1,000-$1,799 tier; at $10,000-$17,999 Joshua Society tier in 2021-22 Honor Roll.'),

    # MARY KUNIK — retired, Austin 78746. Harper-Madison batch 2 line 119.
    ('Kunik, Mary', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $1,000-$1,799 tier (2022-2023 Honor Roll as Mary and Burt Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Mary and Burt Kunik" at $1,000-$1,799 in 2022-2023 Honor Roll; at $10K-$17,999 Joshua Society tier in 2021-22 Honor Roll. Widow of Burt Kunik.'),

    # DARYL KUNIK — principal, TOPO, Austin 78704 (Real Estate).
    # Harper-Madison batch 2 (lines 37, 96) "Kunik, Daryl / principal topo".
    # Youngest son of Burt Kunik; spoke on behalf of family at tribute event.
    ('Kunik, Daryl', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $1,800-$4,999 tier (2022-2023 Honor Roll as Dana and Daryl Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Dana and Daryl Kunik" in 2022-2023 Shalom Austin Honor Roll at $1,800-$4,999 tier; also in 2020-21 and 2021-22 Honor Rolls. Daryl is Burt Kunik\'s youngest son and a leader of TOPO Austin; spoke on behalf of family at JAMen tribute.'),
    ('Kunik, Daryl', 'Shalom Austin - Jewish Austin Men (JAMen) Forum',
     'Member; represented Kunik family at JAMen tribute for father Burt',
     'jewish_civic', 'https://shalomaustin.org/2025/02/25/jamen-jo25/',
     'Shalom Austin article: Daryl Kunik spoke on behalf of the family at Jewish Austin Men event honoring his late father Burt.'),

    # DANA KUNIK — Madwave Trust trustee, Austin 78704. Harper-Madison batch 2 line 126.
    ('Kunik, Dana', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $1,800-$4,999 tier (2022-2023 Honor Roll as Dana and Daryl Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Dana and Daryl Kunik" at $1,800-$4,999 tier on 2022-2023 Shalom Austin Honor Roll; also on 2020-21 and 2021-22 Honor Rolls. Wife of Daryl Kunik.'),

    # RANDALL "RANDY" KUNIK — Austin orthodontist, Kunik Orthodontics, Austin 78746.
    # Harper-Madison batch 2 line 69.
    ('Kunik, Randall', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $1,800-$4,999 tier (2022-2023 Honor Roll as Augustina and Randy Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Augustina and Randy Kunik" at $1,800-$4,999 tier on 2022-2023 Shalom Austin Honor Roll. Dr. Randall L. Kunik is founder of Kunik Orthodontics Austin (since 1991). Member of Burt Kunik extended family.'),
    ('Kunik, Randall', 'Shalom Austin - Jewish Austin Men (JAMen) Forum',
     'Member',
     'jewish_civic', 'https://shalomaustin.org/JAMen/',
     'Randy Kunik (orthodontist) listed among members of Shalom Austin Jewish Austin Men Forum. Part of same extended family as founder Burt Kunik.'),

    # AGUSTINA KUNIK — Kunik Orthodontics marketing, Austin 78746.
    # Harper-Madison batch 2 line 46. Honor Roll lists as "Augustina".
    ('Kunik, Agustina', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $1,800-$4,999 tier (2022-2023 Honor Roll as Augustina and Randy Kunik)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Augustina and Randy Kunik" at $1,800-$4,999 tier on 2022-2023 Shalom Austin Honor Roll. Wife of Dr. Randy Kunik; Kunik Orthodontics marketing executive.'),

    # MAX KUNIK — Wingman's Kitchen, Austin 78741. Harper-Madison batch 1 line 122.
    ('Kunik, Max', 'Shalom Austin - Jewish Austin Men (JAMen) Forum',
     'Member',
     'jewish_civic', 'https://shalomaustin.org/jamen/',
     'Max Kunik listed among members of Shalom Austin Jewish Austin Men Forum; member of Austin Kunik family.'),

    # ==========================================================================
    # AMY & KIRK RUDY — Endeavor Real Estate Group family. Top-tier Shalom Austin donors.
    # ==========================================================================

    # KIRK RUDY — retired, Austin 78703 (Real Estate). Harper-Madison batch 1 lines 82 & 113.
    ('Rudy, Kirk', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $250,000-$499,999 Generations Campaign tier (2021-22 Honor Roll as Amy and Kirk Rudy)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/pkey/2021-22_Shalom_Austin_Honor_Roll/',
     'Listed as "Amy & Kirk Rudy" at $250,000-$499,999 Generations Campaign tier on 2021-22 Shalom Austin Honor Roll. Also appears in 2022-2023 Honor Roll at same tier. The Zeifman Family Early Childhood Program features the Amy & Kirk Rudy ECP Play Area, confirming major naming gift. Kirk is a prior LBJ Humanitarian Award recipient.'),

    # AMY RUDY — retired, Austin 78703. Harper-Madison batch 1 line 102 ("Rudy, Amy / retired").
    ('Rudy, Amy', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $250,000-$499,999 Generations Campaign tier (as Amy and Kirk Rudy)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/pkey/2021-22_Shalom_Austin_Honor_Roll/',
     'Listed as "Amy & Kirk Rudy" at $250,000-$499,999 Generations Campaign tier on Shalom Austin Honor Rolls. Amy & Kirk Rudy ECP Play Area named in their honor at Zeifman Family Early Childhood Program.'),

    # ==========================================================================
    # GOTTESMAN — major Shalom Austin donor family. Pool named in their honor.
    # ==========================================================================

    # SANDY GOTTESMAN — gottesman investments, Austin 78703. Harper-Madison batch 3 line 31.
    ('Gottesman, Sandy', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $25,000-$35,999 King David Society tier (2022-2023 Honor Roll as Lisa and Sandy Gottesman); aquatic center pool named "Lisa and Sandy Gottesman Pool"',
     'jewish_civic', 'https://shalomaustin.org/swimmingatthej/',
     'The Lisa and Sandy Gottesman Pool at the Rochelle & Stanley Ferdman Family Aquatic Center is named for this donor couple. Listed as "Lisa and Sandy Gottesman" at King David Society tier on 2022-2023 Shalom Austin Honor Roll. "JCAA Sandy Gottesman Fund" listed among Shalom Austin Jewish Foundation fundholders.'),

    # LISA GOTTESMAN — unemployed, Austin 78703. Harper-Madison batch 3 line 90.
    ('Gottesman, Lisa', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $25,000-$35,999 King David Society tier (as Lisa and Sandy Gottesman); aquatic pool named in honor',
     'jewish_civic', 'https://shalomaustin.org/swimmingatthej/',
     'Named on the Lisa and Sandy Gottesman Pool at Shalom Austin Ferdman Aquatic Center. Listed at King David Society tier ($25K-$35,999) on 2022-2023 Honor Roll.'),

    # ==========================================================================
    # ADLER / LAND — Former Austin Mayor Steve Adler and wife Diane Land.
    # ==========================================================================

    # STEPHEN ADLER — Austin mayor, 78701. Harper-Madison batch 1 line 147.
    # Second Jewish mayor of Austin.
    ('Adler, Stephen', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $1,800-$4,999 tier (2022-2023 Honor Roll as Hon. Steve Adler & Diane Land)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Hon. Steve Adler & Diane Land" at $1,800-$4,999 tier in 2022-2023 Shalom Austin Honor Roll (also in 2021-22 Honor Roll as "Diane Land & Mayor Steve Adler"). Adler is Austin\'s second Jewish mayor; spoke at Shalom Austin Generations Campaign groundbreaking (2020); described by former Shalom Austin CEO as "a proud Jew, a friend of Israel." Batch: "Adler, Stephen / mayor / Austin 78701" = former mayor Steve Adler.'),

    # DIANE LAND — consultant, self-employed, Austin 78701. Harper-Madison batch 2 line 94.
    # Wife of Steve Adler.
    ('Land, Diane', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $1,800-$4,999 tier (as Hon. Steve Adler & Diane Land)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed jointly with husband Steve Adler on 2022-2023 and 2021-22 Shalom Austin Honor Rolls at $1,800-$4,999 tier. Batch: "Land, Diane / consultant / Self-Employed / Austin 78701" = wife of former Mayor Steve Adler.'),

    # ==========================================================================
    # RANDI SHADE — Austin entrepreneur / former City Council Member. Harper-Madison batch 4 line 107.
    # ==========================================================================
    ('Shade, Randi', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $5,000-$9,999 tier and committee positions (2022-2023 Honor Roll)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Randi Shade & Kayla Shell" on 2022-2023 Shalom Austin Honor Roll at $5K-$9,999 tier with committee positions; also 2021-22 Honor Roll at Pomegranate/Chai ($1,800-$4,999). Board member of Texas Sigma Delta Tau Educational Foundation that established Marilyn Saikin Stahl Sigma Delta Tau Leadership Endowment Fund with initial $60,000 to the Shalom Austin Jewish Foundation. Former Austin City Council member.'),

    # ==========================================================================
    # MILLIE SEGAL — retired, Austin 78703. Harper-Madison batch 2 line 101.
    # ==========================================================================
    ('Segal, Millie', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $500-$999 tier (2022-2023 Honor Roll)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Millie Segal" at $500-$999 tier in 2022-2023 Shalom Austin Honor Roll. Batch: "Segal, Millie / retired / Austin 78703" consistent.'),

    # ==========================================================================
    # HAYLIE SCHWARTZ — at home mom, Austin 78702. Harper-Madison batch 3 line 146.
    # ==========================================================================
    ('Schwartz, Haylie', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $500-$999 tier (2021-22 Honor Roll as Haylie & Jeffrey Schwartz)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/pkey/2021-22_Shalom_Austin_Honor_Roll/',
     'Listed as "Haylie & Jeffrey Schwartz" at $500-$999 tier on 2021-22 Shalom Austin Honor Roll. Batch: "Schwartz, Haylie / at home mom stay / Austin 78702".'),

    # ==========================================================================
    # CODY — Endeavor Real Estate Group / homemaker. Both in Velasquez crawl already;
    # Harper-Madison has them too. Preserve canonical names for Harper-Madison.
    # ==========================================================================

    # BUCK CODY — endeavor real estate investor, Austin 78703. Harper-Madison batch 2 line 26
    # and batch 5 line 9.
    ('Cody, Buck', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $5,000-$9,999 tier Generations Campaign (2022-2023 Honor Roll as Madeleine and Buck Cody)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Madeleine and Buck Cody" at $5K-$9,999 tier (Generations Campaign) on 2022-2023 Shalom Austin Honor Roll. Managing Principal at Endeavor Real Estate Group (Bloomberg profile).'),

    # MADELEINE CODY — homemaker, Austin 78703. Harper-Madison batch 1 line 144.
    ('Cody, Madeleine', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $5,000-$9,999 tier Generations Campaign (as Madeleine and Buck Cody)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Madeleine and Buck Cody" at $5K-$9,999 tier on 2022-2023 Shalom Austin Honor Roll.'),

    # ==========================================================================
    # PASTOR — Andy (Andrew) Pastor = Managing Principal / Co-founder of Endeavor Real Estate.
    # Harper-Madison batch 2 line 38 ("Pastor, Andrew / endeavor estate real / Austin 78732"),
    # batch 2 line 93 ("Pastor, Laura / musician / Austin 78732"), and batch 5 line 15
    # ("Pastor, Andy / erg managing principal / Austin 78732").
    # ==========================================================================
    ('Pastor, Andrew', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $25,000-$35,999 King David Society tier (2022-2023 Honor Roll as Laura and Andy Pastor); past trustee/development board member Dell Jewish Community Center',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Laura and Andy Pastor" at $25K-$35,999 King David Society tier on 2022-2023 Shalom Austin Honor Roll. Endeavor Real Estate Group team page states Andy Pastor is past member of development board and past trustee of the Dell Jewish Community Center. He, his wife Laura, Bobby Epstein, and Jeff/Val Newberg co-funded a new state-of-the-art bus for Shalom Austin (delivered Oct 2019). Batch "Pastor, Andrew / endeavor estate real / Austin 78732" = Andy Pastor.'),
    ('Pastor, Andrew', 'Dell Jewish Community Center',
     'Past trustee and past development board member',
     'jewish_civic', 'https://www.endeavor-re.com/about/team/andy-pastor/',
     'Endeavor Real Estate Group official team page identifies Andy Pastor as "past member of the development board and past trustee of the Dell Jewish Community Center."'),

    # Same individual listed as "Pastor, Andy" in batch 5.
    ('Pastor, Andy', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $25,000-$35,999 King David Society tier (as Laura and Andy Pastor)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Same person as "Pastor, Andrew" — batch 5 line 15 "Pastor, Andy / erg managing principal / Austin 78732". Listed as "Laura and Andy Pastor" at King David Society tier on 2022-2023 Shalom Austin Honor Roll. Co-founder/Managing Principal Endeavor Real Estate Group.'),
    ('Pastor, Andy', 'Dell Jewish Community Center',
     'Past trustee and past development board member',
     'jewish_civic', 'https://www.endeavor-re.com/about/team/andy-pastor/',
     'Batch 5 "Pastor, Andy" is same individual as Andrew Pastor. Endeavor bio: past trustee of Dell JCC.'),

    # LAURA PASTOR — musician, Austin 78732. Harper-Madison batch 2 line 93. Wife of Andy Pastor.
    ('Pastor, Laura', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $25,000-$35,999 King David Society tier (as Laura and Andy Pastor)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed jointly with husband Andy Pastor at King David Society tier ($25K-$35,999) on 2022-2023 Shalom Austin Honor Roll. Co-funded new Shalom Austin bus with Pastor family, Epsteins, and Newbergs in 2019.'),

    # ==========================================================================
    # NEWBERG — Jeff Newberg is co-founder/Managing Principal Endeavor Real Estate Group;
    # ADL board chair (noted for ADL, but also separate Shalom Austin role here).
    # Harper-Madison batch 2 line 64 ("newberg, jeffrey / endeavor estate group real /
    # Austin 78746"), batch 2 line 96 ("newberg, Valerie / endeavor estate group real"),
    # and batch 5 line 18 ("newberg, jeffrey").
    # ==========================================================================
    ('newberg, jeffrey', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $36,000-$49,999 King David Society tier (2022-2023 Honor Roll as Jeff & Valerie Newberg); co-funded new Shalom Austin bus (2019)',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed as "Jeff & Valerie Newberg" at $36K-$49,999 King David Society tier on 2022-2023 Shalom Austin Honor Roll. Val & Jeff Newberg co-funded a new state-of-the-art bus for Shalom Austin (delivered October 2019) with Pastor and Epstein families. Co-founder and Managing Principal, Endeavor Real Estate Group. Disambiguation: Harper-Madison "newberg, jeffrey / endeavor / 78746" = same Jeff Newberg.'),

    ('newberg, Valerie', 'Shalom Austin (Jewish Federation of Greater Austin)',
     'Donor at $36,000-$49,999 King David Society tier (as Jeff & Valerie Newberg); co-funded new Shalom Austin bus',
     'jewish_civic', 'https://fliphtml5.com/iylbt/kxlw/2022-2023_Shalom_Austin_Honor_Roll/',
     'Listed jointly with husband Jeff at King David Society tier ($36K-$49,999) on 2022-2023 Shalom Austin Honor Roll. Val Newberg serves as Director for Jewish Community Association of Austin (Shalom Austin corporate parent). Co-funded new Shalom Austin bus (2019).'),
    ('newberg, Valerie', 'Jewish Community Association of Austin',
     'Director',
     'jewish_civic', 'https://www.corporationwiki.com/Texas/Austin/valerie-j-newberg/36947810.aspx',
     'Valerie Newberg listed as Director of Jewish Community Association of Austin (the legal corporate entity of Shalom Austin). Batch: "newberg, Valerie / endeavor estate group real / Austin 78746" consistent with Val Newberg, wife of Jeff Newberg.'),
]

added = 0
for row in new:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} Harper-Madison AIPAC/pro-Israel/Jewish civic findings')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations: {cur.fetchone()[0]}')
c.close()
