import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import save_listing, init_db
from scrapers.contact_classifier import extract_and_classify
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')

HASHTAGS = [
    'apartamenttirane',
    'shitjetirane',
    'qiratirane',
    'pronatirane',
    'apartamentdurres',
    'shitjedurres',
    'realestatealba',
    'imobiliarealb',
]

def detect_status(text):
    text_lower = text.lower()
    if 'qira' in text_lower or 'me qera' in text_lower:
        return 'Qira'
    elif 'shitje' in text_lower or 'shes' in text_lower:
        return 'Shitje'
    return 'Unknown'

def detect_location(text):
    text_lower = text.lower()
    if 'tirane' in text_lower or 'tirana' in text_lower:
        return 'Tiranë'
    elif 'durres' in text_lower:
        return 'Durrës'
    elif 'vlore' in text_lower:
        return 'Vlorë'
    elif 'shkoder' in text_lower:
        return 'Shkodër'
    return 'Albania'

def scrape_instagram(max_posts_per_tag=10):
    results = []

    try:
        from instagrapi import Client
    except ImportError:
        print("Instagrapi not installed. Run: pip install instagrapi")
        return results

    try:
        cl = Client()
        session_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ig_session.json')

        if os.path.exists(session_file):
            print("Loading Instagram session...")
            cl.load_settings(session_file)
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        else:
            print("Logging into Instagram...")
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            cl.dump_settings(session_file)

        print("Instagram logged in successfully.")

    except Exception as e:
        print(f"Instagram login error: {e}")
        return results

    for hashtag in HASHTAGS:
        print(f"\nSearching #{hashtag}...")
        try:
            medias = cl.hashtag_medias_recent(hashtag, amount=max_posts_per_tag)

            for media in medias:
                try:
                    listing_id = str(media.pk)
                    caption = media.caption_text or ""
                    image_url = str(media.thumbnail_url or "")
                    profile_url = f"https://www.instagram.com/{media.user.username}/"
                    status = detect_status(caption)
                    location = detect_location(caption)
                    title = caption[:80].replace('\n', ' ') if caption else f"Instagram #{hashtag}"

                    is_new = save_listing(
                        "instagram", listing_id, title,
                        "See post", location, "", caption[:200], image_url, profile_url
                    )

                    if is_new:
                        print(f"  NEW: @{media.user.username} | {status} | {location}")

                        contacts = []
                        if caption:
                            contacts = extract_and_classify(caption, profile_url, 'instagram', status)

                        contact_type = contacts[0]['type'] if contacts else 'unknown'

                        listing = {
                            "source": "instagram",
                            "title": title,
                            "price": "See post",
                            "location": location,
                            "image_url": image_url,
                            "listing_url": profile_url,
                            "contact_type": contact_type,
                            "contacts": contacts,
                            "status": status,
                        }
                        results.append(listing)
                        print(f"  SAVED: @{media.user.username} | {contact_type}")

                    time.sleep(1)

                except Exception as e:
                    print(f"  Post error: {e}")
                    continue

            time.sleep(3)

        except Exception as e:
            print(f"  Hashtag #{hashtag} error: {e}")
            continue

    print(f"\nInstagram done. {len(results)} new listings.")
    return results

if __name__ == "__main__":
    init_db()
    scrape_instagram(max_posts_per_tag=10)
