import json
from collections import Counter
d = json.load(open('travis_research/donorbatch3_18_results.json'))
src = json.load(open('travis_research/donorbatch3_18.json'))
print(len(d), 'records; ids match:', [x['donor_id'] for x in d] == [x['donor_id'] for x in src])
print('names match:', [x['name'] for x in d] == [x['name'] for x in src])
print(Counter(x['confidence'] for x in d))
TAX = {"Government","Healthcare","Real Estate","Energy / Environment","Finance","Retail",
       "Transportation","Nonprofit / Advocacy","Technology","Consulting / PR","Construction",
       "Venture Capital","Media","Education","Engineering","Labor","Legal","Hospitality / Events",
       "Architecture","Entertainment","Self-Employed","Not Employed","Student"}
bad = [x['name'] for x in d if x['industry'] is not None and x['industry'] not in TAX]
print('bad industry labels:', bad or 'none')
print('affiliations:', sum(len(x['affiliations']) for x in d))
