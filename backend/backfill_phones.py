"""
One-time backfill: re-visits all listings missing phone numbers,
extracts phones + contact type, updates DB and sheet.
"""
import sys, os, time, random, re, requests, sqlite3
sys.path.append(os.path.dirname(__file__))

from database import DB_PATH, update_listing_contact
from scrapers.contact_classifier import extract_phone_numbers, classify_by_keywords
from sheets_sync import get_sheet, HEADERS

AGENT_KEYWORDS = [
    'agjenci', 'agjensi', 'real estate', 'kompani', 'agency',
    'imobiliare', 'ndertim', 'developer', 'invest', 'group',
    'shitesit e besuar', 'partner', 'studio', 'zyre'
]
FIZIK_KEYWORDS = [
    'pronar', 'vete pronar', 'shes vete', 'jap me qera vete',
    'kontaktoni pronarin', 'pa agjenci', 'without agency'
]

HEADERS_REQ = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "sq-AL,sq;q=0.9,en-US;q=0.8",
}

def fetch_page_text(url, session):
    try:
        r = session.get(url, headers=HEADERS_REQ, timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"    Fetch error: {e}")
    return ""

def classify_from_text(text):
    text_lower = text.lower()
    for kw in AGENT_KEYWORDS:
        if kw in text_lower:
            return 'agent'
    for kw in FIZIK_KEYWORDS:
        if kw in text_lower:
            return 'fizik'
    return 'unknown'

def detect_status(url, text):
    combined = (url + ' ' + text).lower()
    if 'qera' in combined or 'qira' in combined or 'jepet' in combined:
        return 'Qira'
    elif 'shitet' in combined or 'shitje' in combined:
        return 'Shitje'
    return 'Unknown'

def get_listings_missing_phone():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT listing_id, listing_url, source
        FROM listings
        WHERE (phone = '' OR phone IS NULL)
        AND source IN ('merrjep', 'njoftime')
        ORDER BY found_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def update_sheet_row(sheet, listing_url, phone, ctype, status):
    try:
        all_urls = sheet.col_values(3)
        if listing_url in all_urls:
            row_idx = all_urls.index(listing_url) + 1
            sheet.update(f'A{row_idx}:E{row_idx}',
                         [[phone, ctype, listing_url, '', status]])
    except Exception as e:
        print(f"    Sheet update error: {e}")

def run_backfill():
    listings = get_listings_missing_phone()
    total = len(listings)
    print(f"Found {total} listings to backfill.")

    sheet = get_sheet()
    session = requests.Session()
    updated = 0
    failed = 0

    for i, (listing_id, url, source) in enumerate(listings, 1):
        if not url:
            continue

        print(f"[{i}/{total}] {url[:70]}...")
        text = fetch_page_text(url, session)

        if not text:
            failed += 1
            time.sleep(1)
            continue

        phones = extract_phone_numbers(text)
        phone = phones[0] if phones else ''
        ctype = classify_from_text(text) if text else 'unknown'
        status = detect_status(url, text)

        update_listing_contact(listing_id, phone, ctype, status)

        if phone:
            update_sheet_row(sheet, url, phone, ctype, status)
            updated += 1
            print(f"    → {phone} | {ctype} | {status}")
        else:
            print(f"    → no phone found")

        # polite delay to avoid getting blocked
        time.sleep(random.uniform(1.5, 3.0))

        # progress save every 50 listings
        if i % 50 == 0:
            print(f"\n--- Progress: {i}/{total} done, {updated} phones found ---\n")

    print(f"\nBackfill complete. {updated} phones found, {failed} pages failed.")

if __name__ == '__main__':
    run_backfill()
