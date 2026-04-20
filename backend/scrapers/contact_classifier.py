import re
import requests
import time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import save_contact, get_contact_type

AGENT_KEYWORDS = [
    'agjenci', 'agjensi', 'real estate', 'kompani', 'agency',
    'imobiliare', 'ndertim', 'developer', 'invest', 'group',
    'shitesit e besuar', 'partner', 'studio', 'zyre'
]

FIZIK_KEYWORDS = [
    'pronar', 'vete pronar', 'shes vete', 'jap me qera vete',
    'kontaktoni pronarin', 'pa agjenci', 'without agency'
]

def extract_phone_numbers(text):
    patterns = [
        r'06[789]\s?\d{3}\s?\d{4}',
        r'\+355\s?6[789]\s?\d{3}\s?\d{4}',
        r'00355\s?6[789]\s?\d{3}\s?\d{4}',
    ]
    found = set()
    for pattern in patterns:
        for match in re.findall(pattern, text):
            cleaned = re.sub(r'\s+', '', match)
            cleaned = cleaned.replace('+355', '0').replace('00355', '0')
            found.add(cleaned)
    return list(found)

def classify_by_keywords(text):
    text_lower = text.lower()
    for keyword in AGENT_KEYWORDS:
        if keyword in text_lower:
            return 'agent'
    for keyword in FIZIK_KEYWORDS:
        if keyword in text_lower:
            return 'fizik'
    return None

def google_search(phone_number):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = f'https://www.google.com/search?q="{phone_number}"'
        response = requests.get(url, headers=headers, timeout=10)
        text = response.text
        text_lower = text.lower()

        # check if Google results contain agency keywords
        for keyword in AGENT_KEYWORDS:
            if keyword in text_lower:
                print(f'    Google → found agency keyword: {keyword}')
                return 'agent', 'high'

        # check result count
        patterns = [r'About ([\d,]+) results', r'([\d,]+) results']
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                hits = int(match.group(1).replace(',', ''))
                print(f'    Google → {hits} results')
                if hits > 5:
                    return 'agent', hits
                else:
                    return 'fizik', hits

        return 'fizik', 0

    except Exception as e:
        print(f'    Google error: {e}')
        return 'fizik', 0

def classify_contact(phone_number, page_text='', property_link='', platform='', status=''):
    print(f'  Classifying {phone_number}...')

    # step 1: already known in our database
    existing = get_contact_type(phone_number)
    if existing in ('agent', 'fizik'):
        print(f'  {phone_number} → {existing} (already known)')
        save_contact(phone_number, existing, 0)
        return existing

    # step 2: read keywords from the listing page
    keyword_result = None
    if page_text:
        keyword_result = classify_by_keywords(page_text)
        if keyword_result:
            print(f'  {phone_number} → {keyword_result} (from page keywords)')

    # step 3: google the number for more info
    google_result, google_hits = google_search(phone_number)
    time.sleep(2)

    # step 4: combine both results
    # if both agree → use that
    # if keyword says agent → trust it
    # if google says agent → trust it
    # only fizik if BOTH say fizik
    if keyword_result == 'agent' or google_result == 'agent':
        final_type = 'agent'
    elif keyword_result == 'fizik' and google_result == 'fizik':
        final_type = 'fizik'
    elif keyword_result:
        final_type = keyword_result
    else:
        final_type = google_result

    save_contact(phone_number, final_type, google_hits if isinstance(google_hits, int) else 0)

    try:
        import datetime
        from sheets_sync import sync_contact_to_sheet
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        sync_contact_to_sheet(phone_number, final_type, property_link, platform, status, 1, 
                             google_hits if isinstance(google_hits, int) else 0, today)
    except Exception as e:
        print(f'  Sheets sync skipped: {e}')

    print(f'  {phone_number} → {final_type} (keywords: {keyword_result}, google: {google_result})')
    return final_type

def extract_and_classify(text, property_link='', platform='', status=''):
    phones = extract_phone_numbers(text)
    results = []
    for phone in phones:
        contact_type = classify_contact(phone, text, property_link, platform, status)
        results.append({'phone': phone, 'type': contact_type})
    return results
