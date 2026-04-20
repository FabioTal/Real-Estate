import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_property_notification(listing):
    contact_type = listing.get('contact_type', 'unknown')
    contacts = listing.get('contacts', [])
    status = listing.get('status', '')
    source = listing.get('source', '').upper()

    if contacts:
        phones = ', '.join([c['phone'] for c in contacts])
        contact_line = f"📞 {phones}"
    else:
        contact_line = "📞 No phone found"

    if contact_type == 'fizik':
        header = "🚨 PRIVATE SELLER ALERT 🚨"
        type_line = "👤 Type: FIZIK (private person) ✅"
    elif contact_type == 'agent':
        header = "🏢 New Property"
        type_line = "🏢 Type: Agency"
    else:
        header = "🏠 New Property"
        type_line = "❓ Type: Unknown"

    status_line = f"📋 Status: {status}" if status else ""

    message = f"""{header}

🏠 {listing.get('title', 'No title')}
💰 {listing.get('price', 'No price')}
📍 {listing.get('location', 'Unknown')}
{contact_line}
{type_line}
{status_line}
🌐 Source: {source}
🔗 {listing.get('listing_url', '')}"""

    image_url = listing.get('image_url', '')

    try:
        if image_url:
            caption = message if len(message) <= 1024 else message[:1021] + '...'
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
            payload = {
                'chat_id': CHAT_ID,
                'photo': image_url,
                'caption': caption
            }
        else:
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
            payload = {
                'chat_id': CHAT_ID,
                'text': message
            }
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            print(f'  Telegram sent! [{contact_type.upper()}] [{source}]')
        else:
            print(f'  Telegram error: {response.text}')

    except Exception as e:
        print(f'  Telegram exception: {e}')
