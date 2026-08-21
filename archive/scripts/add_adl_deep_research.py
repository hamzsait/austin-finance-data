"""Load deep research findings on the 24 ADL-affiliated Austin individuals."""
import sqlite3, sys, io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except (ValueError, AttributeError):
    pass

c = sqlite3.connect('austin_finance.db', timeout=30)
cur = c.cursor()

# All additional verified affiliations beyond ADL board (which is already in DB)
# Format: (canonical_name, organization, role, category, source_url, notes)
new_records = [
    # === Steve Adler additional ===
    ('Adler, Steve', 'Commonweal Ventures', 'Operating Partner (since 2023)', 'business',
     'https://commonwealventures.com/people/steve-adler', 'Post-mayor venture role'),
    ('Adler, Steve', 'LBJ School of Public Affairs (UT Austin)', 'Adjunct Faculty', 'civic',
     'https://commonwealventures.com/people/steve-adler', 'Also at Huston-Tillotson and St. Edwards'),
    ('Adler, Steve', 'Long Center for the Performing Arts', 'Board Member', 'civic',
     'https://en.wikipedia.org/wiki/Steve_Adler_(politician)', 'Past board service'),
    ('Adler, Steve', 'Breakthrough Austin', 'Board Member', 'civic',
     'https://en.wikipedia.org/wiki/Steve_Adler_(politician)', 'Education nonprofit'),
    ('Adler, Steve', 'Texas Tribune', 'Board Member', 'civic',
     'https://en.wikipedia.org/wiki/Steve_Adler_(politician)', 'Texas-focused news nonprofit'),

    # === Jason Berkowitz ===
    ('Berkowitz, Jason', 'RPM Living (formerly Roscoe Property Management)', 'Founder & CEO (founded 2002)', 'business',
     'https://linkedin.com/in/jason-berkowitz-b0917310', '4th largest US multifamily property mgmt firm; 4,600+ employees post-2021 CF Real Estate merger'),

    # === Cotter Cunningham ===
    ('Cunningham, Cotter', 'RetailMeNot', 'Founder/CEO (2009); Chairman', 'business',
     'https://www.crunchbase.com/person/cotter-cunningham', 'IPO 2013; sold 2017 to Harland Clarke for $630M'),
    ('Cunningham, Cotter', 'Next Coast Ventures', 'Entrepreneur-in-Residence / Venture Partner', 'business',
     'https://nextcoastventures.com', 'Austin VC firm'),
    ('Cunningham, Cotter', 'Waterloo Greenway', 'Board Chair', 'civic',
     'https://www.crunchbase.com/person/cotter-cunningham', 'Austin parks/conservancy'),
    ('Cunningham, Cotter', 'UT Austin Innovation Board', "President's Austin Innovation Board", 'civic',
     'https://www.crunchbase.com/person/cotter-cunningham', ''),
    ('Cunningham, Cotter', 'Bankrate', 'Former SVP/COO', 'business',
     'https://business.vanderbilt.edu/board-bio/cotter-cunningham', 'Led 1999 IPO'),

    # === Laura Gottesman ===
    ('Gottesman, Laura', 'Gottesman Residential Real Estate', 'Founder, Broker/Owner/CEO', 'business',
     'https://gottesmanresidential.com', 'Luxury real estate, $2.2B+ in sales'),
    ('Gottesman, Laura', 'Greater Austin Economic Development Board', 'Board Member', 'civic',
     'https://friendsaustin.org/about/board/laura-gottesman', ''),
    ('Gottesman, Laura', 'Dell Medical School Founders Circle', 'Member', 'healthcare',
     'https://friendsaustin.org/about/board/laura-gottesman', ''),
    ('Gottesman, Laura', 'Friends of the Children - Austin', 'Board Member', 'civic',
     'https://friendsaustin.org/about/board/laura-gottesman', ''),

    # === Morris Gottesman ===
    ('Gottesman, Morris', 'US Capital Wealth Advisors LLC', 'Senior Managing Director, The Gottesman Group', 'business',
     'https://uscallc.com', 'Joined 2014; Senior Managing Member 2021'),
    ('Gottesman, Morris', 'Seton Forum', 'Past President', 'healthcare',
     'https://linkedin.com/in/morrisgottesman', ''),
    ('Gottesman, Morris', 'Children\'s Hospital Foundation', 'Former Chairman', 'healthcare',
     'https://linkedin.com/in/morrisgottesman', ''),
    ('Gottesman, Morris', 'Dell Children\'s Medical Foundation', 'Former Treasurer', 'healthcare',
     'https://linkedin.com/in/morrisgottesman', ''),

    # === Diane Land ===
    ('Land, Diane', 'Trammell Crow Company', 'Former Real Estate Professional (14 years)', 'business',
     'https://linkedin.com/in/diane-land-3226ba4', 'Connection point with Kirk Rudy, Jeff Newberg, Bryce Miller (all ex-Trammell Crow)'),
    ('Land, Diane', 'Coopers & Lybrand', 'Former (4 years - real estate and oil & gas tax)', 'business',
     'https://linkedin.com/in/diane-land-3226ba4', ''),
    ('Land, Diane', 'Courageous Conversation Global Foundation', 'Board Member', 'civic',
     'https://ccglobalfoundation.org/about/diane-tipton-land', ''),

    # === Audrey & Raymond Maislin ===
    ('Maislin, Audrey', 'Shalom Austin Women\'s Philanthropy Lion of Judah', 'Member', 'jewish_civic',
     'https://shalomaustin.org', ''),
    ('Maislin, Audrey', 'City of Austin', '2022 Key to the City honoree', 'civic',
     'https://austin.adl.org/events/past', 'Presented by Mayor Steve Adler'),
    ('Maislin, Raymond', 'City of Austin', '2022 Key to the City honoree', 'civic',
     'https://austin.adl.org/events/past', 'Presented by Mayor Steve Adler'),

    # === Jeff Newberg ===
    ('Newberg, Jeff', 'Endeavor Real Estate Group', 'Co-Founder & Managing Principal (1999)', 'business',
     'https://endeavor-re.com/about/team/jeff-newberg', 'Active Austin real estate since 1984; lead developer of Domain NORTHSIDE'),
    ('Newberg, Jeff', 'Trammell Crow Company', 'Former Managing Director, Austin Retail Division', 'business',
     'https://endeavor-re.com/about/team/jeff-newberg', 'Pre-Endeavor; same firm as Kirk Rudy, Bryce Miller, Diane Land'),
    ('Newberg, Jeff', 'Shalom Austin', 'Director / Leadership', 'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl', ''),
    ('Newberg, Jeff', 'JCC Association of North America', 'Board of Directors', 'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl', 'National-level JCC board'),
    ('Newberg, Jeff', 'Rotary Club of Austin Westlake', 'Member', 'civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl', ''),
    ('Newberg, Jeff', 'Shalom Austin Israel Mission Trip', 'Co-Chair (with Val Newberg)', 'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl', ''),

    # === Val Newberg ===
    ('Newberg, Val', 'Shalom Austin National Women\'s Philanthropy', 'Board Member', 'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl', ''),
    ('Newberg, Val', 'Shalom Austin Israel Mission Trip', 'Co-Chair (with Jeff Newberg)', 'jewish_civic',
     'https://shalomaustin.org/2023/08/31/jo-sep23-adl', ''),

    # === Edie Rogat ===
    ('Rogat, Edie', 'Ballet Austin', 'Board Member, Former Board Chair', 'civic',
     'https://balletaustin.org', ''),
    ('Rogat, Edie', 'Ballet Austin Foundation', 'Trustee, current Vice Chair', 'civic',
     'https://balletaustin.org', ''),
    ('Rogat, Edie', 'Ernst & Young', 'Former Management Consultant', 'business',
     'https://theorg.com/org/ballet-austin-incorporated', ''),
    ('Rogat, Edie', 'Smithsonian Institution', 'Former Public Programs Planner', 'civic',
     'https://theorg.com/org/ballet-austin-incorporated', ''),

    # === Amy Rudy ===
    ('Rudy, Amy', 'Shalom Austin Zeifman Family Early Childhood Program', 'Amy & Kirk Rudy ECP Play Area namesake', 'jewish_civic',
     'https://shalomaustin.org', ''),

    # === Kirk Rudy (additional beyond what's already in DB) ===
    ('Rudy, Kirk', 'Trammell Crow Company', 'Former City Leader, Austin', 'business',
     'https://endeavor-re.com', 'National "top producer" 1997'),
    ('Rudy, Kirk', 'Hill Country Conservancy', 'Board Member', 'civic',
     'https://keywiki.org/Kirk_Rudy', ''),
    ('Rudy, Kirk', 'The Long Center', 'Board Member', 'civic',
     'https://keywiki.org/Kirk_Rudy', ''),
    ('Rudy, Kirk', 'Austin Area Urban League', 'Board Member', 'civic',
     'https://keywiki.org/Kirk_Rudy', ''),
    ('Rudy, Kirk', 'Greater Austin Chamber of Commerce', 'Board Member', 'civic',
     'https://keywiki.org/Kirk_Rudy', ''),
    ('Rudy, Kirk', 'Opportunity Austin (Greater Austin EDC)', 'Board Member', 'civic',
     'https://keywiki.org/Kirk_Rudy', ''),

    # === Mark Salmanson ===
    ('Salmanson, Mark', 'Leadership Austin', 'Board of Directors', 'civic',
     'https://leadershipaustin.org/alumni/alumni-directory/results/mark-salmanson', 'Essential 12 program 1991'),
    ('Salmanson, Mark', 'Temple Beth Shalom', 'President / Lifelong Learning Co-Chair', 'jewish_civic',
     'https://corporationwiki.com', ''),
    ('Salmanson, Mark', 'Jewish Community Center (JCC) of Austin', 'Past Chair', 'jewish_civic',
     'https://communitymatters.biz/2010/01/17/mark-salmansons-50th', ''),

    # === Eugene Sepulveda ===
    ('Sepulveda, Eugene', 'Entrepreneurs Foundation of Central Texas', 'CEO (since April 2005)', 'business',
     'https://culturati.info', ''),
    ('Sepulveda, Eugene', 'Capital Factory', 'Director and Partner', 'business',
     'https://capitalfactory.com', 'Major Austin tech accelerator'),
    ('Sepulveda, Eugene', 'Steve Adler Mayoral Campaign', 'Senior Advisor and former Campaign Treasurer', 'political',
     'https://linkedin.com/in/eugenesepulveda', 'Direct connection to Adler'),
    ('Sepulveda, Eugene', 'Greater Austin Chamber of Commerce', 'Past Vice-Chair', 'civic',
     'https://linkedin.com/in/eugenesepulveda', ''),
    ('Sepulveda, Eugene', 'Leadership Austin', 'Past Board Chair (1999)', 'civic',
     'https://linkedin.com/in/eugenesepulveda', ''),
    ('Sepulveda, Eugene', 'Austin Community Foundation', 'Past Trustee and Investment Chair', 'civic',
     'https://linkedin.com/in/eugenesepulveda', ''),
    ('Sepulveda, Eugene', 'Texas Tribune', 'Board Member', 'civic',
     'https://linkedin.com/in/eugenesepulveda', ''),
    ('Sepulveda, Eugene', 'Obama 2012 National Finance Committee', 'Member; Co-chair LGBT Leadership Council', 'political',
     'https://linkedin.com/in/eugenesepulveda', 'Top-25 fundraiser nationally per FEC; raised $1M+'),
    ('Sepulveda, Eugene', 'UT McCombs School of Business', 'Former Adjunct Faculty (MBA and undergrad)', 'civic',
     'https://linkedin.com/in/eugenesepulveda', ''),

    # === Dave Shaw ===
    ('Shaw, Dave', 'Arrow', 'Founder and President', 'business',
     'https://arrowatwork.com/team', 'Austin branding/PR/communications firm; clients incl American Airlines, AT&T'),
    ('Shaw, Dave', 'Annette Strauss Institute for Civic Life (UT Austin)', 'Advisory Council', 'civic',
     'https://straussinstitute.moody.utexas.edu', 'Moody College'),
    ('Shaw, Dave', 'Texas Lyceum', 'Past Chair', 'civic',
     'https://linkedin.com/in/therealdaveshaw', ''),
    ('Shaw, Dave', 'Mission Capital', 'Past Chair', 'civic',
     'https://linkedin.com/in/therealdaveshaw', ''),
    ('Shaw, Dave', 'Austin Library Foundation', 'Past Chair', 'civic',
     'https://linkedin.com/in/therealdaveshaw', ''),

    # === Jan Soifer ===
    ('Soifer, Jan', '345th District Court of Travis County', 'Judge (elected 2016, re-elected 2020/2024)', 'political',
     'https://jansoifer.com/about', 'Civil and family cases'),
    ('Soifer, Jan', 'Travis County Democratic Party', 'Chair (May 2013-Sept 2015)', 'political',
     'https://jansoifer.com/about', 'Raised $1M+, coordinated 2014 election'),
    ('Soifer, Jan', 'J Street', 'National Advisory Council Member', 'liberal_zionist',
     'https://jansoifer.com/about', 'Liberal Zionist organization'),
    ('Soifer, Jan', 'Interfaith Action of Central Texas (iACT)', 'Past President', 'civic',
     'https://jansoifer.com/about', ''),
    ('Soifer, Jan', 'Congregation Beth Israel of Austin', 'Past President', 'jewish_civic',
     'https://jansoifer.com/about', ''),
    ('Soifer, Jan', 'Jewish Community Relations Council of Austin', 'Past Chair', 'jewish_civic',
     'https://jansoifer.com/about', ''),
    ('Soifer, Jan', 'Jewish Federation of Austin', 'Past Vice President (4 years)', 'jewish_civic',
     'https://jansoifer.com/about', ''),
    ('Soifer, Jan', 'Austin Bar Association', 'Past President', 'civic',
     'https://jansoifer.com/about', ''),
    ('Soifer, Jan', 'Texas Office of the Attorney General', 'Former Chief, Charitable Trusts Section', 'business',
     'https://jansoifer.com/about', ''),

    # === Robyn Sperling ===
    ('Sperling, Robyn', 'Shalom Austin Early Childhood Program', 'Chair', 'jewish_civic',
     'https://shalomaustin.org/mosaic', '~30 years of Shalom Austin service'),
    ('Sperling, Robyn', 'Lion of Judah / Pomegranate Society', 'Chair', 'jewish_civic',
     'https://shalomaustin.org/mosaic', 'Shalom Austin Womens Philanthropy'),

    # === Lynne Stein ===
    ('Stein, Lynne', 'Shalom Austin Women\'s Philanthropy Lion of Judah', '$5K+ annual donor', 'jewish_civic',
     'https://shalomaustin.org/wplions', ''),

    # === Steven Tomlinson ===
    ('Tomlinson, Steven', 'Seminary of the Southwest', 'Associate Professor of Leadership and Administration', 'civic',
     'https://ssw.edu', 'Episcopal seminary in Austin'),
    ('Tomlinson, Steven', 'Acton School of Business', 'Founding Master Teacher', 'business',
     'https://steventomlinson.com/about', 'Entrepreneurship school'),
    ('Tomlinson, Steven', 'Episcopal Diocese of Texas', 'Ordained Priest (Jan 2024)', 'civic',
     'https://ssw.edu/the-rev-steven-tomlinson-ordained-to-the-priesthood', ''),
    ('Tomlinson, Steven', 'UT Austin Economics Dept', 'Former Assistant Professor of Economics', 'civic',
     'https://steventomlinson.com/about', 'PhD Stanford Economics; hired at 28'),

    # === Marc Winkelman ===
    ('Winkelman, Marc', 'Calendar Holdings / Calendar Club LLC / Go! Retail Group', 'CEO and Co-Founder (1993)', 'business',
     'https://crunchbase.com/person/marc-winkelman', '1,200+ pop-up bookstores nationwide'),
    ('Winkelman, Marc', 'Elie Wiesel Foundation for Humanity', 'Secretary', 'jewish_civic',
     'https://texasbookfestival.org/directory/board-advisor/marc-winkelman', ''),
    ('Winkelman, Marc', 'National Jewish Democratic Council', 'Secretary', 'liberal_zionist',
     'https://texasbookfestival.org/directory/board-advisor/marc-winkelman', 'Liberal Zionist political org'),
    ('Winkelman, Marc', 'St. David\'s Community Health Foundation', 'Board of Trustees', 'healthcare',
     'https://texasbookfestival.org/directory/board-advisor/marc-winkelman', ''),
    ('Winkelman, Marc', 'University of Texas Press', 'Advisory Council', 'civic',
     'https://texasbookfestival.org/directory/board-advisor/marc-winkelman', ''),
    ('Winkelman, Marc', 'Texas Book Festival', 'Board Advisor', 'civic',
     'https://texasbookfestival.org/directory/board-advisor/marc-winkelman', ''),
    ('Winkelman, Marc', 'Kirkus Reviews', 'Past part-owner', 'business',
     'https://crunchbase.com/person/marc-winkelman', ''),
]

added = skipped = 0
for row in new_records:
    cur.execute('INSERT OR IGNORE INTO civic_affiliations (canonical_name, organization, role, category, source_url, notes) VALUES (?,?,?,?,?,?)', row)
    if cur.rowcount:
        added += 1
    else:
        skipped += 1

c.commit()
print(f'Added {added} new affiliations | Skipped {skipped} duplicates')
cur.execute('SELECT COUNT(*) FROM civic_affiliations')
print(f'Total civic affiliations now: {cur.fetchone()[0]}')

# Show what we have for each ADL person
print()
print('=== Affiliation count per ADL-tied individual ===')
adl_names = ['Adler, Steve', 'Berkowitz, Jason', 'Cunningham, Cotter', 'Gottesman, Laura',
             'Gottesman, Morris', 'Land, Diane', 'Maislin, Audrey', 'Maislin, Raymond',
             'Newberg, Jeff', 'Newberg, Val', 'Rogat, Edie', 'Rudy, Amy', 'Rudy, Deborah',
             'Rudy, Kirk', 'Rudy, Rick', 'Salmanson, Mark', 'Sepulveda, Eugene', 'Shaw, Dave',
             'Soifer, Jan', 'Sperling, Robyn', 'Stein, Lynne', 'Tomlinson, Steven',
             'Waxman, Judy', 'Winkelman, Marc', 'Winkelman, Suzanne']
for name in adl_names:
    cur.execute('SELECT COUNT(*) FROM civic_affiliations WHERE canonical_name = ?', (name,))
    n = cur.fetchone()[0]
    print(f'  {name:<25} {n} affiliations')

c.close()
