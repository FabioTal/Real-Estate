import gspread
from google.oauth2.service_account import Credentials
import os

SHEET_ID = '128WxuDWiK9BeyuLk5LMgD3HOJAxrBD_ZKysZ7gfpfNQ'
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

HEADERS = ['Phone', 'Type', 'Property Link', 'Platform', 'Status', 'Post Count', 'Google Hits', 'First Seen']

def get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet

def setup_headers(sheet):
    sheet.update('A1:H1', [HEADERS])

def sync_contact_to_sheet(phone, contact_type, property_link='', platform='', status='', post_count=1, google_hits=0, first_seen=''):
    try:
        sheet = get_sheet()
        setup_headers(sheet)

        all_phones = sheet.col_values(1)
        if phone in all_phones:
            row_index = all_phones.index(phone) + 1
            sheet.update(f'B{row_index}:H{row_index}', [[contact_type, property_link, platform, status, post_count, google_hits, first_seen]])
            print(f'  Sheet updated: {phone} → {contact_type}')
        else:
            sheet.append_row([phone, contact_type, property_link, platform, status, post_count, google_hits, first_seen])
            print(f'  Sheet added: {phone} → {contact_type}')

    except Exception as e:
        print(f'  Sheets sync error: {e}')

if __name__ == '__main__':
    sync_contact_to_sheet(
        '0691234567', 'fizik',
        'https://www.merrjep.al/njoftim/apartament-2-1-tirane/123456',
        'merrjep', 'Qira', 1, 3, '2026-04-19'
    )
    print('Test done — check your Google Sheet!')
