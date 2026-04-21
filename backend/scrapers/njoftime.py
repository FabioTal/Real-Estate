import requests
from bs4 import BeautifulSoup
import sys
import os
import time
import random
import hashlib
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import save_listing, update_listing_contact, init_db
from scrapers.contact_classifier import extract_and_classify

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "sq-AL,sq;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.njoftime.com",
}

BASE_URL = "https://www.njoftime.com"

FORUMS = [
    {"id": "shtepi-ne-shitje.4",     "status": "Shitje"},
    {"id": "shtepi-me-qera.5",        "status": "Qira"},
    {"id": "apartamente-ne-shitje.6", "status": "Shitje"},
    {"id": "apartamente-me-qera.7",   "status": "Qira"},
    {"id": "prona-te-ndryshme.8",     "status": "Unknown"},
]

def get_listing_id(href):
    parts = href.rstrip("/").split(".")
    if parts and parts[-1].isdigit():
        return parts[-1]
    return hashlib.md5(href.encode()).hexdigest()[:12]

def get_page_text(session, url):
    try:
        response = session.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text()
    except Exception as e:
        print(f"  Error fetching page: {e}")
        return ""

def detect_location(text):
    text_lower = text.lower()
    if "tirane" in text_lower or "tirana" in text_lower:
        return "Tiranë"
    elif "durres" in text_lower:
        return "Durrës"
    elif "vlore" in text_lower:
        return "Vlorë"
    elif "shkoder" in text_lower:
        return "Shkodër"
    elif "elbasan" in text_lower:
        return "Elbasan"
    elif "korce" in text_lower:
        return "Korçë"
    return "Albania"

def scrape_njoftime(max_pages=2):
    results = []
    session = requests.Session()

    try:
        session.get(BASE_URL, headers=HEADERS, timeout=10)
        time.sleep(random.uniform(1, 2))
    except Exception as e:
        print(f"Njoftime connection error: {e}")
        return results

    for forum in FORUMS:
        for page_num in range(1, max_pages + 1):
            url = f"{BASE_URL}/forums/{forum['id']}/?page={page_num}"
            print(f"\nScraping Njoftime: {url}")

            try:
                response = session.get(url, headers=HEADERS, timeout=15)
                print(f"Status: {response.status_code}")

                if response.status_code != 200:
                    print(f"  Skipping — bad status")
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                thread_links = soup.find_all("a", href=True)
                listings_map = {}

                for a in thread_links:
                    href = a.get("href", "")
                    if "/threads/" not in href:
                        continue
                    listing_id = get_listing_id(href)
                    title_text = a.get_text(strip=True)

                    if listing_id not in listings_map:
                        listings_map[listing_id] = {"href": href, "title": ""}
                    if title_text and len(title_text) > 10 and not title_text[0].isdigit():
                        listings_map[listing_id]["title"] = title_text

                print(f"Found {len(listings_map)} listings")
                saved_count = 0

                for listing_id, data in listings_map.items():
                    href = data["href"]
                    title_text = data["title"]

                    if not title_text or len(title_text) < 8:
                        continue

                    full_url = BASE_URL + href if href.startswith("/") else href
                    status = forum["status"]
                    location = detect_location(title_text)

                    price = "No price"
                    if "€" in title_text:
                        try:
                            price = title_text.split("€")[0].strip().split()[-1] + " €"
                        except:
                            price = "See listing"

                    is_new = save_listing(
                        "njoftime", listing_id, title_text,
                        price, location, "", "", "", full_url
                    )

                    if is_new:
                        print(f"  NEW: {title_text[:60]}")
                        page_text = get_page_text(session, full_url)
                        time.sleep(random.uniform(1, 2))

                        contacts = []
                        if page_text:
                            contacts = extract_and_classify(page_text, full_url, 'njoftime', status)

                        contact_type = contacts[0]['type'] if contacts else 'unknown'
                        phone = contacts[0]['phone'] if contacts else ''
                        update_listing_contact(listing_id, phone, contact_type, status)

                        listing = {
                            "source": "njoftime",
                            "title": title_text,
                            "price": price,
                            "location": location,
                            "image_url": "",
                            "listing_url": full_url,
                            "contact_type": contact_type,
                            "contacts": contacts,
                            "status": status,
                        }
                        results.append(listing)
                        saved_count += 1
                        print(f"  SAVED: {title_text[:50]} | {status} | {contact_type}")

                print(f"Saved {saved_count} new from this page")
                time.sleep(random.uniform(2, 4))

            except Exception as e:
                print(f"Error: {e}")
                continue

    print(f"\nNjoftime done. {len(results)} new listings.")
    return results

if __name__ == "__main__":
    init_db()
    scrape_njoftime(max_pages=1)
