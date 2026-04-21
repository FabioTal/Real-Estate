import gspread
from google.oauth2.service_account import Credentials
import os
import datetime

SHEET_ID = '128WxuDWiK9BeyuLk5LMgD3HOJAxrBD_ZKysZ7gfpfNQ'
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
HEADERS = ['Phone', 'Type', 'Property Link', 'Platform', 'Status', 'Post Count', 'Google Hits', 'First Seen']

def detect_status_from_url(url):
    url = (url or '').lower()
    if 'qera' in url or 'qira' in url or 'jepet' in url or 'rent' in url:
        return 'Qira'
    elif 'shitet' in url or 'shitje' in url or 'sale' in url:
        return 'Shitje'
    return 'Unknown'

def get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def save_listing_to_sheet(listing):
    """Append one row to Sheet1 for every new listing found."""
    try:
        sheet = get_sheet()

        # Ensure header exists
        if sheet.row_values(1) != HEADERS:
            sheet.update('A1:H1', [HEADERS])

        contacts = listing.get('contacts', [])
        phone      = contacts[0]['phone'] if contacts else ''
        ctype      = listing.get('contact_type', 'unknown')
        url        = listing.get('listing_url', '')
        platform   = listing.get('source', '').lower()
        status     = listing.get('status', '')
        today      = datetime.datetime.now().strftime('%Y-%m-%d')

        sheet.insert_rows([[phone, ctype, url, platform, status, 1, 0, today]],
                          row=2, value_input_option='RAW')
        print(f'  Sheet saved: {listing.get("title", "")[:50]}')

    except Exception as e:
        print(f'  Sheet error: {e}')

def sync_contact_to_sheet(phone, contact_type, property_link='', platform='', status='', post_count=1, google_hits=0, first_seen=''):
    """Called by contact_classifier for newly classified phones — updates existing row or appends."""
    try:
        sheet = get_sheet()

        if sheet.row_values(1) != HEADERS:
            sheet.update('A1:H1', [HEADERS])

        all_phones = sheet.col_values(1)
        if phone in all_phones:
            row_index = all_phones.index(phone) + 1
            sheet.update(f'B{row_index}:H{row_index}',
                         [[contact_type, property_link, platform, status, post_count, google_hits, first_seen]])
        else:
            sheet.append_row([phone, contact_type, property_link, platform, status, post_count, google_hits, first_seen],
                             value_input_option='USER_ENTERED')
            print(f'  Sheet added: {phone} → {contact_type}')

    except Exception as e:
        print(f'  Sheet contact error: {e}')

def bulk_sync_db_to_sheet(db_rows):
    """Write all DB listings into the table starting at row 2."""
    try:
        sheet = get_sheet()

        if sheet.row_values(1) != HEADERS:
            sheet.update('A1:H1', [HEADERS])

        rows_to_write = []
        for row in db_rows:
            fields = list(row) + ['', 'unknown', '']
            source      = fields[1] or ''
            listing_url = fields[9] or ''
            found_at    = (fields[10] or '')[:10]
            phone       = str(fields[11]) if len(fields) > 11 and fields[11] else ''
            ctype       = fields[12] if len(fields) > 12 and fields[12] else 'unknown'
            status      = fields[13] if len(fields) > 13 and fields[13] else detect_status_from_url(listing_url)
            # ensure phone keeps leading zero
            if phone and not phone.startswith('0'):
                phone = '0' + phone
            rows_to_write.append([phone, ctype, listing_url, source, status, 1, 0, found_at])

        if rows_to_write:
            sheet.insert_rows(rows_to_write, row=2, value_input_option='RAW')
            print(f'  Bulk synced {len(rows_to_write)} listings.')
        else:
            print('  No data to sync.')

    except Exception as e:
        print(f'  Bulk sync error: {e}')
