import sys
import os
import time
import random
import requests
import json
from bs4 import BeautifulSoup
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import save_listing, init_db

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "sq-AL,sq;q=0.9,en-US;q=0.8",
}

SEARCH_QUERIES = [
    "site:facebook.com/marketplace apartament tirane shitje",
    "site:facebook.com/marketplace apartament tirane qera",
    "site:facebook.com/marketplace shtepi tirane shitje",
    "site:facebook.com/marketplace apartament durres",
    "site:facebook.com/marketplace vila albania shitje",
]


def search_google_for_fb(query, max_results=10):
    results = []
    try:
        from googlesearch import search
        print(f"Googling: {query}")
        for url in search(query, num_results=max_results, lang="sq"):
            if "facebook.com" in url:
                results.append(url)
                print(f"  Found: {url}")
            time.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        print(f"Google search error: {e}")
    return results


def get_fb_listing_details(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        title = ""
        title_el = soup.find("meta", property="og:title")
        if title_el:
            title = title_el.get("content", "")

        description = ""
        desc_el = soup.find("meta", property="og:description")
        if desc_el:
            description = desc_el.get("content", "")

        image_url = ""
        img_el = soup.find("meta", property="og:image")
        if img_el:
            image_url = img_el.get("content", "")

        price = "No price"
        if "EUR" in description or "€" in description:
            words = description.split()
            for i, w in enumerate(words):
                if "EUR" in w or "€" in w:
                    price = words[max(0, i-1)] + " " + w
                    break

        return title, description, image_url, price

    except Exception as e:
        print(f"  Error fetching FB listing: {e}")
        return "", "", "", "No price"


def scrape_facebook(max_results_per_query=10):
    all_results = []

    for query in SEARCH_QUERIES:
        urls = search_google_for_fb(query, max_results=max_results_per_query)

        for url in urls:
            listing_id = url.split("/")[-1] or url.split("/")[-2]
            if not listing_id:
                continue

            title, description, image_url, price = get_fb_listing_details(url)

            if not title:
                title = query.replace("site:facebook.com/marketplace ", "").title()

            location = "Albania"
            if "tirane" in query:
                location = "Tiranë"
            elif "durres" in query:
                location = "Durrës"

            is_new = save_listing(
                "facebook", listing_id, title,
                price, location, "", description, image_url, url
            )

            if is_new:
                listing = {
                    "source": "facebook",
                    "title": title,
                    "price": price,
                    "location": location,
                    "image_url": image_url,
                    "listing_url": url,
                    "description": description
                }
                all_results.append(listing)
                print(f"  NEW: {title[:50]} | {price} | {location}")

            time.sleep(random.uniform(1, 2))

        time.sleep(random.uniform(3, 5))

    print(f"\nDone. {len(all_results)} new Facebook listings saved.")
    return all_results


if __name__ == "__main__":
    init_db()
    scrape_facebook(max_results_per_query=10)
    