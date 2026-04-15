"""Load ADL findings for Harper-Madison donors."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

new = [
    # (canonical_name, organization, role, category, source_url, notes)

    # Jeff Newberg - Endeavor Real Estate Group co-founder / Managing Principal.
    # ADL Austin past board chair (4th chair), longtime National Commissioner, 2023 Golden Door honoree.
    # Filed in Harper-Madison batches as "newberg, jeffrey" (lowercase) at Austin 78746.
    ('newberg, jeffrey', 'Anti-Defamation League (ADL) Austin',
     'Past Board Chair (4th Chair); National Commissioner; 2023 Golden Door Awards honoree',
     'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl/',
     'Shalom Austin Sep 2023 ("Choosing Hope in a World of Hate") confirms Jeff served as ADL Austin\'s 4th board chair and that he and Val Newberg were honored at the 2023 Golden Door Awards Dinner (Oct 30, 2023). Disambiguation: donor employer "endeavor estate group real" and 78746 Austin address match Jeff Newberg, Endeavor Real Estate Group co-founder/Managing Principal. Same individual canonically listed as "Newberg, Jeff" in other campaigns.'),

    # Val Newberg - longtime ADL Austin board member, 2023 Golden Door Awards honoree.
    # Filed in Harper-Madison batch 2 as "newberg, Valerie" at Austin 78746 (same household as Jeff).
    ('newberg, Valerie', 'Anti-Defamation League (ADL) Austin',
     'Longtime Board Member; 2023 Golden Door Awards honoree',
     'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl/',
     'Shalom Austin Sep 2023 piece describes Val Newberg as "a longtime ADL board member and dedicated volunteer"; honored with husband Jeff Newberg at 2023 ADL Austin Golden Door Awards Dinner. Disambiguation: same 78746 Austin address as Jeff Newberg with "endeavor estate group real" employer; wife of Jeff Newberg. Also canonically listed as "Newberg, Val" or "Newberg, Valerie" in other campaigns.'),

    # Dan Graham - Notley co-founder; 2016 ADL Austin True Colors honoree (Vision in Action Award).
    # Appears in Harper-Madison batch_2 (Notley partner, Austin 78721) and batch_3 (Austin 78730).
    ('Graham, Dan', 'Anti-Defamation League (ADL) Austin',
     '2016 True Colors honoree (Vision in Action Award)',
     'jewish_civic',
     'https://austin.culturemap.com/news/society/09-09-16-anti-defamation-league-true-colors-2016/',
     'CultureMap Austin coverage of ADL Austin 5th annual True Colors event (Sep 2016) identifies Dan and Lisa Graham as honorees celebrated "for their work to advance social justice and civil rights." Disambiguation: Harper-Madison donor employer "notley partner ventures" / "a build ceo sign" matches Dan Graham, Notley co-founder and BuildASign co-founder.'),

    # Lisa Graham - Notley co-founder/CEO; 2016 ADL Austin True Colors honoree.
    # Appears in Harper-Madison batch_2 (fund notley owner, Austin 78721) and batch_3 (homemaker, Austin 78730).
    ('Graham, Lisa', 'Anti-Defamation League (ADL) Austin',
     '2016 True Colors honoree',
     'jewish_civic',
     'https://austin.culturemap.com/news/society/09-09-16-anti-defamation-league-true-colors-2016/',
     'CultureMap Austin coverage of ADL Austin 5th annual True Colors event (Sep 2016) identifies Lisa and Dan Graham as honorees. Disambiguation: Harper-Madison donor employer "fund notley owner" (Austin 78721) matches Lisa Graham, Notley co-founder/CEO. Same household as Dan Graham.'),

    # Stephen (Steve) Adler - Former Austin Mayor (2015-2023); ADL Austin Board Chair 2009-2012.
    # Received 2017 Raymond and Audrey Maislin Humanitarian Award at ADL Golden Door Gala.
    # Harper-Madison batch_1 row 147: "Adler, Stephen" (mayor, Austin 78701).
    ('Adler, Stephen', 'Anti-Defamation League (ADL) Austin',
     'Past Board Chair (2009-2012); 2017 Raymond & Audrey Maislin Humanitarian Award honoree',
     'jewish_civic',
     'https://en.wikipedia.org/wiki/Steve_Adler_(politician)',
     'Wikipedia bio (sourced from ADL and news coverage) confirms: "From 2009 to 2012, Adler served as the board chair of the Anti-Defamation League Austin Region where he contributed to the creation of the Austin Hate Crimes Task Force." ADL Austin Facebook (Dec 2017) confirms Adler and Diane T. Land received 2017 Maislin Humanitarian Award at Golden Door Gala. Disambiguation: Harper-Madison donor listed as occupation "mayor" at 78701 matches Steve Adler, Austin Mayor 2015-2023.'),

    # Diane Land - DT Land Group / First Lady of Austin (Stephen Adler\'s wife).
    # Co-recipient of 2017 Raymond and Audrey Maislin Humanitarian Award at ADL Golden Door Gala.
    # Harper-Madison batch_2 row 94: "Land, Diane" (consultant, Austin 78701).
    ('Land, Diane', 'Anti-Defamation League (ADL) Austin',
     '2017 Raymond & Audrey Maislin Humanitarian Award honoree (with husband Steve Adler)',
     'jewish_civic',
     'https://www.facebook.com/ADLAustin/videos/adl-honors-mayor-steve-adler-diane-t-land/1686295158100429/',
     'ADL Austin Facebook video (2017) titled "ADL Honors Mayor Steve Adler & Diane T. Land" confirms she received the Raymond and Audrey Maislin Humanitarian Award with husband Stephen Adler at the 2017 Golden Door Gala. Disambiguation: Harper-Madison donor Diane Land at Austin 78701 (same household as Adler donor row) matches Diane T. Land, spouse of former Mayor Adler, DT Land Group principal.'),

    # Eugene Sepulveda - CEO Entrepreneurs Foundation; 2022 ADL Austin Golden Door honoree
    # (Raymond and Audrey Maislin Humanitarian Award, with husband Steven Tomlinson).
    # Harper-Madison batches list name REVERSED as "Eugene, Sepulveda" (batch_2 #135; batch_3 #106).
    ('Eugene, Sepulveda', 'Anti-Defamation League (ADL) Austin',
     '2022 Raymond & Audrey Maislin Humanitarian Award honoree; prior 2010 Torch of Liberty Co-Chair',
     'jewish_civic',
     'https://shalomaustin.org/2022/12/01/adl-golden-door/',
     'Shalom Austin Dec 2022 "ADL Austin Honors Eugene Sepulveda and Steven Tomlinson at Golden Door Awards Dinner" confirms 2022 Maislin Humanitarian Award at JW Marriott Oct 25, 2022. Disambiguation: Harper-Madison filings list name first/last reversed ("Eugene, Sepulveda") with employer "ceo entrepreneurs foundation" at Austin 78705, matching Eugene Sepulveda, CEO of Entrepreneurs Foundation and Culturati co-founder.'),

    # Steven Tomlinson - Seminary of the Southwest professor; 2022 ADL Austin Golden Door honoree.
    # Harper-Madison batch_3 row 21: name REVERSED and MISSPELLED as "Steven, Tomlison"
    # (employer "of professor seminary southwest the", Austin 78705).
    ('Steven, Tomlison', 'Anti-Defamation League (ADL) Austin',
     '2022 Raymond & Audrey Maislin Humanitarian Award honoree (with husband Eugene Sepulveda)',
     'jewish_civic',
     'https://ssw.edu/dr-steven-tomlinson-and-eugene-sepulveda-presented-humanitarian-award-by-anti-defamation-league/',
     'Seminary of the Southwest news item confirms Dr. Steven Tomlinson and Eugene Sepulveda received the 2022 Raymond and Audrey Maislin Humanitarian Award from ADL. Disambiguation: Harper-Madison filing has first/last reversed and surname misspelled as "Tomlison"; employer "of professor seminary southwest the" at Austin 78705 matches Steven Tomlinson, Associate Professor of Leadership and Administration at Seminary of the Southwest. Same person canonically listed as "Tomlinson, Steven" in other filings.'),

    # Randi Shade - Former Austin City Council Member (2008-2011); former Executive Council Member
    # of the Austin Chapter of Anti-Defamation League per her public LinkedIn profile.
    # Harper-Madison batch_4 row 107: "Shade, Randi" (homemaker, Austin 78703).
    ('Shade, Randi', 'Anti-Defamation League (ADL) Austin',
     'Former Executive Council Member, Austin Chapter',
     'jewish_civic',
     'https://www.linkedin.com/in/randi-shade-6a6b8289/',
     'Randi Shade\'s public LinkedIn profile lists her as "former Executive Council Member of Austin Chapter of Anti-Defamation League" (repeatedly indexed in Google search snippets). She and fellow council members Sheryl Cole and Laura Morrison formally engaged ADL Austin in 2010 to develop the city-led hate crimes task force. Disambiguation: only one Randi Shade in Austin 78703 politically active; former City Council Member 2008-2011 and entrepreneur.'),
]

added = 0
for row in new:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount: added += 1
c.commit()
print(f'Added {added} ADL-tied Harper-Madison donors')
c.close()
