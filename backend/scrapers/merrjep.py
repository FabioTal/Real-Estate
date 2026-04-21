import asyncio
import sys
import os
import random
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import save_listing, update_listing_contact, init_db
from scrapers.contact_classifier import extract_and_classify
from playwright.async_api import async_playwright

def detect_status(text):
    text_lower = text.lower()
    if 'qira' in text_lower or 'rent' in text_lower:
        return 'Qira'
    elif 'shitje' in text_lower or 'shet' in text_lower or 'sale' in text_lower:
        return 'Shitje'
    return 'Unknown'

async def get_listing_details(page, url):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1500)

        price = "No price"
        try:
            price_el = await page.query_selector("[class*='price'], [class*='Price']")
            if price_el:
                price = await price_el.inner_text()
        except:
            pass

        location = "Unknown"
        try:
            loc_el = await page.query_selector("[class*='location'], [class*='city'], [class*='Location']")
            if loc_el:
                location = await loc_el.inner_text()
        except:
            pass

        image_url = ""
        try:
            img_meta = await page.query_selector("meta[property='og:image']")
            if img_meta:
                image_url = await img_meta.get_attribute("content") or ""
        except:
            pass

        description = ""
        try:
            desc_meta = await page.query_selector("meta[property='og:description']")
            if desc_meta:
                description = await desc_meta.get_attribute("content") or ""
        except:
            pass

        page_text = await page.inner_text("body")

        return price.strip(), location.strip(), image_url, description, page_text

    except Exception as e:
        print(f"  Error fetching details: {e}")
        return "No price", "Unknown", "", "", ""


async def scrape_merrjep(category="apartamente", location="tirane", max_pages=2):
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="sq-AL",
        )

        page = await context.new_page()

        print("Opening homepage...")
        await page.goto("https://www.merrjep.al", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        for page_num in range(1, max_pages + 1):
            url = f"https://www.merrjep.al/njoftime/imobiliare-vendbanime/{category}/{location}?Page={page_num}"
            print(f"\nScraping page {page_num}: {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"  Page load error: {e}")
                continue

            all_links = await page.query_selector_all("a[href]")
            listing_links = []
            seen_ids = set()

            for a in all_links:
                href = await a.get_attribute("href") or ""
                if "/njoftim/" in href and href.count("/") >= 2:
                    listing_id = href.split("/")[-1]
                    if listing_id and listing_id not in seen_ids:
                        seen_ids.add(listing_id)
                        listing_links.append(href)

            print(f"Found {len(listing_links)} listings on page {page_num}")

            for href in listing_links:
                full_url = "https://www.merrjep.al" + href if href.startswith("/") else href
                listing_id = href.split("/")[-1]
                slug = href.split("/")[-2] if len(href.split("/")) > 2 else ""
                title_text = slug.replace("-", " ").title()
                status = detect_status(slug)

                is_new = save_listing(
                    "merrjep", listing_id, title_text,
                    "", "", "", "", "", full_url
                )

                if is_new:
                    print(f"  NEW listing found: {title_text[:50]} — fetching details...")

                    price, loc_text, image_url, description, page_text = await get_listing_details(page, full_url)
                    await page.wait_for_timeout(random.randint(500, 1500))

                    # refine status from full page text
                    if status == 'Unknown':
                        status = detect_status(page_text)

                    save_listing(
                        "merrjep", listing_id, title_text,
                        price, loc_text, "", description, image_url, full_url
                    )

                    contacts = []
                    if page_text:
                        contacts = extract_and_classify(page_text, full_url, 'merrjep', status)

                    contact_type = contacts[0]['type'] if contacts else 'unknown'
                    phone = contacts[0]['phone'] if contacts else ''
                    update_listing_contact(listing_id, phone, contact_type, status)

                    listing = {
                        "source": "merrjep",
                        "title": title_text,
                        "price": price,
                        "location": loc_text,
                        "image_url": image_url,
                        "listing_url": full_url,
                        "description": description,
                        "contact_type": contact_type,
                        "contacts": contacts,
                        "status": status,
                    }
                    results.append(listing)
                    print(f"  SAVED: {title_text[:50]} | {price} | {status} | {contact_type}")

            await page.wait_for_timeout(2000)

        await browser.close()

    print(f"\nDone. {len(results)} new listings found.")
    return results


if __name__ == "__main__":
    init_db()
    asyncio.run(scrape_merrjep(category="apartamente", location="tirane", max_pages=1))
